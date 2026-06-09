# JWT 인증 서비스 단위 테스트 (RED 단계)
import time
import pytest
from jose import JWTError


class TestPasswordHashing:
    """bcrypt 비밀번호 해싱/검증 테스트"""

    def test_hash_password_returns_bcrypt_hash(self):
        """해시 결과가 bcrypt 형식($2b$...)으로 시작해야 한다"""
        from stock_picker.auth.service import hash_password
        result = hash_password("mypassword")
        assert result.startswith("$2b$")

    def test_hash_password_is_different_each_time(self):
        """같은 비밀번호라도 salt 때문에 매번 다른 해시가 생성된다"""
        from stock_picker.auth.service import hash_password
        h1 = hash_password("mypassword")
        h2 = hash_password("mypassword")
        assert h1 != h2

    def test_verify_password_correct(self):
        """올바른 비밀번호 검증은 True를 반환해야 한다"""
        from stock_picker.auth.service import hash_password, verify_password
        hashed = hash_password("correct_pass")
        assert verify_password("correct_pass", hashed) is True

    def test_verify_password_wrong(self):
        """틀린 비밀번호 검증은 False를 반환해야 한다"""
        from stock_picker.auth.service import hash_password, verify_password
        hashed = hash_password("correct_pass")
        assert verify_password("wrong_pass", hashed) is False


class TestJWTTokens:
    """JWT access/refresh 토큰 생성 및 검증 테스트"""

    def test_create_access_token_returns_string(self):
        """access token이 문자열로 반환되어야 한다"""
        from stock_picker.auth.service import create_access_token
        token = create_access_token({"sub": "testuser"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token_returns_string(self):
        """refresh token이 문자열로 반환되어야 한다"""
        from stock_picker.auth.service import create_refresh_token
        token = create_refresh_token({"sub": "testuser"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token_returns_subject(self):
        """유효한 토큰 디코드 시 sub 값이 반환되어야 한다"""
        from stock_picker.auth.service import create_access_token, decode_token
        token = create_access_token({"sub": "testuser"})
        payload = decode_token(token)
        assert payload.sub == "testuser"

    def test_decode_token_has_exp(self):
        """토큰 페이로드에 만료 시간(exp)이 포함되어야 한다"""
        from stock_picker.auth.service import create_access_token, decode_token
        token = create_access_token({"sub": "testuser"})
        payload = decode_token(token)
        assert payload.exp is not None
        assert payload.exp > int(time.time())

    def test_decode_invalid_token_raises_jwt_error(self):
        """잘못된 토큰은 JWTError를 발생시켜야 한다"""
        from stock_picker.auth.service import decode_token
        with pytest.raises(JWTError):
            decode_token("invalid.token.here")

    def test_access_token_different_from_refresh_token(self):
        """access 토큰과 refresh 토큰은 달라야 한다 (만료 시간 다름)"""
        from stock_picker.auth.service import create_access_token, create_refresh_token
        data = {"sub": "testuser"}
        access = create_access_token(data)
        refresh = create_refresh_token(data)
        assert access != refresh
