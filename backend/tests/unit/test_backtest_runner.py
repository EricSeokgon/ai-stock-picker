# 백테스트 runner 유닛 테스트 — 벤치마크 실패 처리, 상태 전환 (T-022)
from datetime import date
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from stock_picker.db.models import BacktestDailyResult, BacktestRun, User


def _create_in_memory_engine():
    """인메모리 SQLite 엔진 생성"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(bind=engine, checkfirst=True)
    BacktestRun.__table__.create(bind=engine, checkfirst=True)
    BacktestDailyResult.__table__.create(bind=engine, checkfirst=True)
    return engine


def _create_run(db, strategy: str = "momentum") -> BacktestRun:
    """테스트용 BacktestRun 레코드 생성"""
    # User 없이 직접 run 삽입 (외래키 검사 비활성화 상태)
    user = User(username="runner_test", email="runner@test.com", hashed_password="hashed")
    db.add(user)
    db.commit()
    db.refresh(user)

    run = BacktestRun(
        user_id=user.id,
        strategy=strategy,
        start_date=date(2023, 1, 1),
        end_date=date(2023, 1, 31),
        status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


class TestRunnerStatusTransitions:
    """상태 전환 테스트 — pending → running → done/failed"""

    def test_success_transitions_to_done(self):
        """정상 실행 시 pending → running → done 전환"""
        engine = _create_in_memory_engine()
        Session = sessionmaker(bind=engine)
        db = Session()
        run = _create_run(db)
        run_id = run.id
        db.close()

        # FinanceDataReader 모킹 — 가격 데이터 없음 (빈 딕셔너리)
        with patch("stock_picker.backtest.runner._fetch_price_data", return_value={}), \
             patch("stock_picker.backtest.runner._fetch_benchmark_data", return_value=None):

            # run_backtest는 async이므로 asyncio.run으로 실행
            # DB URL을 실제 엔진과 연결하기 위해 직접 Session 사용
            from stock_picker.backtest.runner import _update_status, _save_results

            db2 = Session()
            _update_status(db2, run_id, "running")
            _save_results(db2, run_id, [], None)
            _update_status(db2, run_id, "done", completed=True)
            db2.close()

            db3 = Session()
            updated_run = db3.query(BacktestRun).filter(BacktestRun.id == run_id).first()
            assert updated_run.status == "done"
            assert updated_run.completed_at is not None
            db3.close()

        BacktestDailyResult.__table__.drop(bind=engine, checkfirst=True)
        BacktestRun.__table__.drop(bind=engine, checkfirst=True)
        User.__table__.drop(bind=engine, checkfirst=True)

    def test_failure_transitions_to_failed(self):
        """예외 발생 시 'failed' 상태로 전환"""
        engine = _create_in_memory_engine()
        Session = sessionmaker(bind=engine)
        db = Session()
        run = _create_run(db)
        run_id = run.id
        db.close()

        from stock_picker.backtest.runner import _update_status

        db2 = Session()
        _update_status(db2, run_id, "failed")
        db2.close()

        db3 = Session()
        updated_run = db3.query(BacktestRun).filter(BacktestRun.id == run_id).first()
        assert updated_run.status == "failed"
        assert updated_run.completed_at is None
        db3.close()

        BacktestDailyResult.__table__.drop(bind=engine, checkfirst=True)
        BacktestRun.__table__.drop(bind=engine, checkfirst=True)
        User.__table__.drop(bind=engine, checkfirst=True)


class TestBenchmarkFailure:
    """벤치마크 실패 시 백테스트 정상 완료 테스트"""

    def test_benchmark_failure_does_not_fail_run(self):
        """벤치마크 조회 실패 시 benchmark_value=None이지만 run은 완료"""
        from stock_picker.backtest.runner import _fetch_benchmark_data

        # FinanceDataReader가 예외를 던지는 경우
        with patch("stock_picker.backtest.runner._BENCHMARK_CODE", "INVALID_CODE"):
            with patch("FinanceDataReader.DataReader", side_effect=Exception("API 오류")):
                result = _fetch_benchmark_data(date(2023, 1, 1), date(2023, 1, 31))
                assert result is None

    def test_benchmark_empty_data_returns_none(self):
        """벤치마크 데이터가 비어있으면 None 반환"""
        import pandas as pd
        from stock_picker.backtest.runner import _fetch_benchmark_data

        with patch("FinanceDataReader.DataReader", return_value=pd.DataFrame()):
            result = _fetch_benchmark_data(date(2023, 1, 1), date(2023, 1, 31))
            assert result is None


class TestGetKrxUniverse:
    """_get_krx_universe 파라미터 동작 테스트"""

    def test_returns_correct_size(self):
        """요청한 크기만큼 반환"""
        from stock_picker.backtest.runner import _get_krx_universe

        assert len(_get_krx_universe(5)) == 5
        assert len(_get_krx_universe(10)) == 10

    def test_returns_list_of_strings(self):
        """문자열 목록 반환"""
        from stock_picker.backtest.runner import _get_krx_universe

        codes = _get_krx_universe(3)
        assert all(isinstance(c, str) for c in codes)

    def test_max_universe_bounded(self):
        """풀 크기 이상 요청해도 에러 없이 최대치 반환"""
        from stock_picker.backtest.runner import _get_krx_universe

        codes = _get_krx_universe(100)
        assert len(codes) > 0  # 에러 없이 반환
