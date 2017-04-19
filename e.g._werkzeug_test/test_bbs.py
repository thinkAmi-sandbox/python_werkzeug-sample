import os
import ast
from werkzeug import Client
# WerkzeugのResponseオブジェクトについて
# http://werkzeug.pocoo.org/docs/0.11/wrappers/#mixin-classes
from werkzeug.wrappers import Response
import bottle
from bottle_app.bbs import app


class TestRequest(object):
    @classmethod
    def setup_class(cls):
        # wsgi-interceptでBottleをテストする場合、デフォルトではテンプレートディレクトリを認識しない
        # そのため、以下に従い、mod_wsgiと同じくディレクトリを指定すること
        # http://bottlepy.org/docs/dev/faq.html#template-not-found-in-mod-wsgi-mod-python
        current_dir = os.path.abspath(os.path.dirname(__file__))
        template_dir = os.path.join(current_dir, 'bottle_app/views')
        bottle.TEMPLATE_PATH.insert(0, template_dir)


    def teardown_method(self):
        """テストごとにpickleファイルができるため、お互いに影響を与えないよう削除する"""
        if os.path.exists('bbs.pickle'):
            os.remove('bbs.pickle')


    def get_cookie_value(self, client, name):
        # > CookieJar オブジェクトは保管されている Cookie オブジェクトをひとつずつ取り出すための、イテレータ(iterator)・プロトコルをサポートしています。
        # https://docs.python.jp/3/library/http.cookiejar.html#cookiejar-and-filecookiejar-objects
        # イテレータから条件にマッチした最初のものを取得する
        # http://stackoverflow.com/questions/9868653/find-first-list-item-that-matches-criteria
        # https://docs.python.jp/3/library/functions.html#next
        cookie = next((c for c in client.cookie_jar if c.name == name), None)
        if cookie:
            # Cookieオブジェクトの属性など
            # https://docs.python.jp/3/library/http.cookiejar.html#cookie-objects
            return self.convert_cookie_value_to_unicode_str(cookie)
        return None

        # forループを使う場合
        # for c in client.cookie_jar:
        #     if c.name == name:
        #         return self.convert_cookie_value_to_unicode_str(c)
        # return None


    @staticmethod
    def convert_cookie_value_to_unicode_str(cookie):
        print(cookie.value)
        #=> "\343\203\217\343\203\263\343\203\211\343\203\253\345\220\2153"
        after_literal_eval = ast.literal_eval(cookie.value)
        print(after_literal_eval)
        #=> ãã³ãã«
        encoded = after_literal_eval.encode('latin1')
        print(encoded)
        #=> b'\xe3\x83\x8f\xe3\x83\xb3\xe3\x83\x89\xe3\x83\xab\xe5\x90\x8d3'
        decoded = encoded.decode('utf-8')
        print(decoded)
        #=> ハンドル名3
        return decoded


    def test_get(self):
        # http://werkzeug.pocoo.org/docs/0.11/test/#werkzeug.test.Client
        sut = Client(app, Response)
        actual = sut.get('/')
        # http://werkzeug.pocoo.org/docs/0.11/wrappers/#werkzeug.wrappers.BaseResponse.status_code
        assert actual.status_code == 200
        # http://werkzeug.pocoo.org/docs/0.11/wrappers/#werkzeug.wrappers.BaseResponse.headers
        assert actual.headers.get('Content-Type') == 'text/html; charset=UTF-8'
        # デフォルトではバイト文字列になるので、as_text=Trueで文字列化する
        # http://werkzeug.pocoo.org/docs/0.11/wrappers/#werkzeug.wrappers.BaseResponse.get_data
        # ただし、バグがあるので、utf-8以外の文字コードは扱えない(現時点でもcloseしていない)
        # http://blog.amedama.jp/entry/2016/06/11/225137
        # https://github.com/pallets/werkzeug/issues/947
        body = actual.get_data(as_text=True)
        assert 'テスト掲示板' in body


    def test_post_without_redirect(self):
        form = {
            'title': 'タイトル1',
            'handle': 'ハンドル名1',
            'message': 'メッセージ1',
        }
        sut = Client(app, Response)
        actual = sut.post('/', data=form)
        assert actual.status_code == 303
        assert actual.headers['content-type'] == 'text/html; charset=UTF-8'
        # bottleでredirect()を使った場合、bodyは''になる
        assert actual.get_data(as_text=True) == ''


    def test_post_with_redirect(self):
        form = {
            'title': 'タイトル2',
            'handle': 'ハンドル名2',
            'message': 'メッセージ2',
        }
        sut = Client(app, Response)
        # Werkzeugのドキュメントには見当たらなかったが、Flaskと同じようにしたら動作
        # http://flask.pocoo.org/docs/0.12/testing/#logging-in-and-out
        actual = sut.post('/', data=form, follow_redirects=True)
        assert actual.status_code == 200
        assert actual.headers['content-type'] == 'text/html; charset=UTF-8'
        body = actual.get_data(as_text=True)
        assert 'テスト掲示板' in body
        assert 'タイトル2' in body
        assert 'ハンドル名2' in body
        assert 'メッセージ2' in body


    def test_cookie(self):
        form = {
            'title': 'タイトル3',
            'handle': 'ハンドル名3',
            'message': 'メッセージ3',
        }
        sut = Client(app, Response)
        actual = sut.post('/', data=form, follow_redirects=True)
        print(type(sut.cookie_jar))
        #=> <class 'werkzeug.test._TestCookieJar'>
        actual_cookie = self.get_cookie_value(sut, 'handle')
        assert actual_cookie == 'ハンドル名3'
