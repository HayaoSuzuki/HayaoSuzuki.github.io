# DjangoのModelバリデーションを求めて

*2024-04-24 公開*

Django 3.0から、Modelを定義する際に`Choices`クラスが使えるようになった。
以前から、Modelの`Field`クラスには`choices`引数を指定できた。
`choices`引数の渡し方は基本的にタプルのリストであり、単純な構造ながら面倒であった。
`Choices`クラスは実質的に列挙型であり、`Field`の選択肢を列挙型で指定できる。
タプルのリストと比較して、選択肢同士の関係が列挙型でより密接になり、扱いやすくなったと言える。

## 選択肢を出したのだから選択肢から選んでよ

次のような例を考える。

```python
from django.db import models


class Number(models.IntegerChoices):
    ACE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13


class Suit(models.TextChoices):
    DIAMOND = "♢", "ダイヤ"
    SPADE = "♠", "スペード"
    HEART = "♡", "ハート"
    CLUB = "♣", "クラブ"


class Card(models.Model):
    number = models.IntegerField(choices=Number)
    suit = models.CharField(max_length=1, choices=Suit)

    def __str__(self) -> str:
        return f"{self.suit}{self.number}"
```

トランプのカードを想定した(説明するためだけに存在する)`Card`モデルである。
`Card`モデルはフィールドとして数値とスートを持つ。

## `Field` の `choices` に期待していたもの

`number = models.IntegerField(choices=Number)`と書いたからには、`Card`モデルのレコードの`number`には1から13以外の数字は入って欲しくない、と思うだろう。
1から13以外の数字が指定された場合はよしなに弾いてくれる、と思うだろう。
しかし、思うだけでは何も進まない。
本当にそうなのか、ユニットテストを書いてみよう。

```python
import pytest
from django.db.utils import DatabaseError

from ..models import Card, Number, Suit


@pytest.mark.django_db
class TestCardModel:
    @pytest.mark.parametrize("number", Number)
    @pytest.mark.parametrize("suit", Suit)
    def test_card_creation(self, number: Number, suit: Suit):
        card = Card.objects.create(number=number, suit=suit)

        assert card.number == number
        assert card.suit == suit
        assert str(card) == f"{suit}{number}"

    @pytest.mark.parametrize("number,suit", ((14, Suit.SPADE), (Number.ACE, "★")))
    def test_invalid_argument(self, number: Number, suit: Suit):
        with pytest.raises(DatabaseError):
            Card.objects.create(number=number, suit=suit)
```

奇妙なデータは作られないと信じているが、果たしてどうだろうか。

```bash
(.venv) $ tox -e test
test: commands[0]> pytest .

...
___________________________________________________________ TestCardModel.test_invalid_argument[1-★] ____________________________________________________________

self = <sample.tests.test_models.TestCardModel object at 0x000001E547E5E060>, number = Number.ACE, suit = '★'

    @pytest.mark.parametrize("number,suit", ((14, Suit.SPADE), (Number.ACE, "★")))
    def test_invalid_argument(self, number: Number, suit: Suit):
>       with pytest.raises(DatabaseError):
E       Failed: DID NOT RAISE <class 'django.db.utils.DatabaseError'>

sample\tests\test_models.py:20: Failed
___________________________________________________________ TestCardModel.test_invalid_argument[14-♠] ___________________________________________________________

self = <sample.tests.test_models.TestCardModel object at 0x000001E547E5DF70>, number = 14, suit = Suit.SPADE

    @pytest.mark.parametrize("number,suit", ((14, Suit.SPADE), (Number.ACE, "★")))
    def test_invalid_argument(self, number: Number, suit: Suit):
>       with pytest.raises(DatabaseError):
E       Failed: DID NOT RAISE <class 'django.db.utils.DatabaseError'>

sample\tests\test_models.py:20: Failed
```

期待していた動作は、想定していない値を入れたら弾く、である。
しかし、ユニットテストの結果からわかるのは、`Card`モデルが想定していない値を受け入れていることである。

## CHECK制約

`choices`は何をするのか。
[Djangoの公式ドキュメント](https://docs.djangoproject.com/ja/5.0/ref/models/fields/#django.db.models.Field.choices)を確認してみよう。

> choices が指定された場合、 モデルのバリデーション によって強制的に、デフォルトのフォームウィジェットが通常のテキストフィールドの代わりにこれらの選択肢を持つセレクトボックスになります。

つまり、デフォルトのフォームウィジェットはセレクトボックスになるが、Modelのフィールドに渡せる値を制限することはできない。
我々はドキュメントを碌に読まず、`choices`を過信していたようだ。

それではどうすればよいのか。
CHECK制約である。

`Card`モデルを次のように変更しよう。

```python
class Card(models.Model):
    number = models.IntegerField(choices=Number)
    suit = models.CharField(max_length=1, choices=Suit)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(number__in=Number.values), name="number_check"
            ),
            models.CheckConstraint(
                check=models.Q(suit__in=Suit.values), name="suit_check"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.suit}{self.number}"
```

このように、`Choices`をCHECK制約に渡せば、Modelが受け入れる値の種類を制限できる。

## `__empty__` 属性の落とし穴

`Choices`クラスには`__empty__`属性を指定してラベル付きの空値を設けることができる。

```python
class Number(models.IntegerChoices):
    ACE = 1
    # ...
    KING = 13

    __empty__ = "選択してください"
```

しかし、`__empty__`属性を指定した状態の`Choices`をそのままCHECK制約に渡してしまうと、制約の条件として`None`を許容してしまう事象が発生する。
マイグレーションを見ると、`None`が候補に混ざっていることがわかる。

```python
        migrations.AddConstraint(
            model_name="card",
            constraint=models.CheckConstraint(
                check=models.Q(("number__in", [None, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])),
                name="number_check",
            ),
        ),
        migrations.AddConstraint(
            model_name="card",
            constraint=models.CheckConstraint(
                check=models.Q(("suit__in", [None, "♢", "♠", "♡", "♣"])),
                name="suit_check",
            ),
        ),
```

今回のケースだと、`number`と`suit`いずれのフィールドもNOT NULLであるため、`None`を渡しても期待通りエラーが発生するが、NULLを許容する場合は素通りしてしまう。
実害は(おそらく)ないが、念のため気を付けたほうが良いだろう。

## `Choices` と `ModelForm`

以上の例だけだと、Modelのフィールドに`choices`を渡すのはそれほど有益ではない、と感じるかもしれない。
`choices`や`Choices`の真価は`ModelForm`にある。

`Card`モデルに対応するModelFormを書く。

```python
from django.forms import ModelForm

from .models import Card


class CardModelForm(ModelForm):
    class Meta:
        model = Card
        fields = ["number", "suit"]
```

これに対応するユニットテストも書く。

```python
import pytest

from ..forms import CardModelForm
from ..models import Number, Suit


@pytest.mark.django_db
class TestCardForm:
    @pytest.mark.parametrize("number", Number)
    @pytest.mark.parametrize("suit", Suit)
    def test_valid_form(self, number: Number, suit: Suit):
        form_data = {"number": number, "suit": suit}
        form = CardModelForm(data=form_data)

        assert form.is_valid()

        card = form.save()
        assert card.number == number
        assert card.suit == suit

    def test_blank_data(self):
        form = CardModelForm(data={})

        assert not form.is_valid()
        assert len(form.errors) == 2

    @pytest.mark.parametrize("number,suit", ((14, Suit.SPADE), (Number.ACE, "★")))
    def test_invalid_data(self, number: Number, suit: Suit):
        form_data = {"number": number, "suit": suit}
        form = CardModelForm(data=form_data)

        assert not form.is_valid()
        assert len(form.errors) == 1

    @pytest.mark.parametrize("number,suit", ((None, Suit.SPADE), (Number.ACE, None)))
    def test_invalid_data_with_none(self, number: Number, suit: Suit):
        form_data = {"number": number, "suit": suit}
        form = CardModelForm(data=form_data)

        assert not form.is_valid()
        assert len(form.errors) == 1
```

このテストは期待通りに動く。
つまり、Modelのフィールドの`choices`引数に`Choices`クラス(または従来からあるリストのタプル)を渡した上で、Modelに対応するModelFormを書くと、我々が想像していた`choices`のバリデーションが手に入る。
適切なModelFormが手に入るのだ。
ユーザから入力を受け取るような場面では役に立つだろう。
ただし、上記の例の通り、CHECK制約を設定しない限り、フォームを使わずに`Card.objects.create()`を使うと想定していない値を持つ`Card`のレコードが生成できてしまう点には注意が必要である。

## Hypothesisでユニットテストを強化する

ここまでのユニットテストを観察してみよう。

- 正常ケースでは、数値およびスートの組み合わせをすべてテストしている。これはテストケースが高々52通りなのですべてチェックできる。
- 失敗ケースでは、数値が不正の例、スートが不正の例をそれぞれ1ケースしかテストできていない。
    - 数値の境界値は0と14だが、本当にこれだけだろうか。
    - スートとして入る文字列は多数にある。すべての文字などテストできるはずもない。

事前にデータを固定する従来のユニットテストの手法だけでは、想定していない失敗ケースを見過ごしている可能性が生じる。
ここでプロパティベーステストの出番である。

[Hypothesis](https://hypothesis.readthedocs.io)は、Python向けのプロパティベーステストのライブラリである。
プロパティベーステストは、生成された多数の入力データに対してプロパティ(性質)が満たされるかどうかをテストする手法である。
HaskellのQuickCheckライブラリが初出で、現在は各プログラミング言語に移植されている。
従来のユニットテストがデータを固定していたのに対し、プロパティベーステストはデータが満たすプロパティを指定し、実際のテストケースはライブラリが生成してくれる。
人力では発見しにくいバグが見つかりやすくなるのだ。

なお、僕は『[ロバストPython](https://www.oreilly.co.jp/books/9784814400171/)』でHypothesisの存在を知った。
とても良い本なので、是非読んでみてほしい(監訳しました)。

### Model のテストの書き換え ― 正常ケース

まずは正常ケースから。
`@pytest.mark.parametrize`の二重適用を、`@hypothesis.given`でまとめて書ける。

```python
import hypothesis
import hypothesis.strategies as st
import pytest

from ..models import Card, Number, Suit


@pytest.mark.django_db
class TestCardModel:
    @hypothesis.given(
        number=st.sampled_from(Number.values),
        suit=st.sampled_from(Suit.values),
    )
    def test_card_creation(self, number: int, suit: str):
        card = Card.objects.create(number=number, suit=suit)

        assert card.number == number
        assert card.suit == suit
        assert str(card) == f"{suit}{number}"
```

`st.sampled_from()`は、引数で渡したイテラブルから1つ取り出すストラテジ(strategy)である。
Hypothesisは`@hypothesis.given`デコレータでストラテジを指定することで、そのストラテジから生成した値をテスト関数に渡してくれる。
候補が少ないイテラブル(今回ならスート4種、数値13種)は`st.sampled_from()`が手軽だ。

### Model のテストの書き換え ― 失敗ケース

次に、「想定していないスート」に関するプロパティを考える。
今回のケースだと「`("♢", "♠", "♡", "♣")`以外の文字」である。
また、「想定する数値」に関するプロパティは「1から13」である。
これをHypothesisで書くと次のようになる。

```python
    @hypothesis.given(
        number=st.integers(min_value=1, max_value=13),
        suit=st.characters(exclude_characters=Suit.values) | st.just(None),
    )
    def test_invalid_suit(self, number: int, suit: str):
        with pytest.raises(DatabaseError):
            Card.objects.create(number=number, suit=suit)
```

`st.integers()`は整数を生成するストラテジである。
最大値や最小値はオプションであるが、今回は「1から13」が欲しいので両方指定した。
`st.characters()`は長さ1の文字列(つまり文字)を生成するストラテジである。
オプションで細かく制御できるが、今回は`Suit.values`を除外した文字を生成する設定を行った。
これで「`("♢", "♠", "♡", "♣")`以外の文字」のプロパティが実現できた。
`st.just()`は常に単一の値を返すストラテジである。
ここで面白いのが、ストラテジ同士を`|`で連結できることだ。
`A | B`は、AまたはBのいずれかのストラテジから値を生成するストラテジになる。
したがって`st.characters(exclude_characters=Suit.values) | st.just(None)`は、「`("♢", "♠", "♡", "♣")`以外の文字、または`None`」を生成するストラテジになる。

次に、「想定していない数値」に関するプロパティとそのテストを書く。

```python
    @hypothesis.given(
        number=st.integers(min_value=14) | st.integers(max_value=0) | st.just(None),
        suit=st.sampled_from(Suit.values),
    )
    def test_invalid_number(self, number: int, suit: str):
        with pytest.raises(DatabaseError):
            Card.objects.create(number=number, suit=suit)
```

`st.integers()`単体では「0以下の整数、または14以上の整数」は指定できないので、`|`で連結して実現している。

実際にテストを走らせてみよう。
結果を抜粋する。

```
E           self = <django.db.backends.sqlite3.base.SQLiteCursorWrapper object at 0x000002819441C050>
E           query = 'INSERT INTO "sample_card" ("number", "suit") VALUES (?, ?) RETURNING "sample_card"."id"', params = (-9223376507952189107, '♢')
E
E               def execute(self, query, params=None):
E                   if params is None:
E                       return super().execute(query)
E                   # Extract names if params is a mapping, i.e. "pyformat" style is used.
E                   param_names = list(params) if isinstance(params, Mapping) else None
E                   query = self.convert_query(query, param_names=param_names)
E           >       return super().execute(query, params)
E           E       OverflowError: Python int too large to convert to SQLite INTEGER
E
E           .tox\test\Lib\site-packages\django\db\backends\sqlite3\base.py:329: OverflowError
```

トランプの数値として`-9223376507952189107`を入れた結果、SQLiteで扱える数値を超えてしまった例外が発生した。
これは境界値分析が足りない例ともいえるし、データベース(今回はSQLite)の制約を想定していなかったともいえる。
いずれにせよ、従来の固定されたテストケースだけでは発見できないバグがプロパティベーステストで発見できたのは素晴らしいことである。

### Form のテストの書き換え

同様にFormのテストもプロパティベーステストに書き換えてみよう。

```python
import hypothesis
import hypothesis.strategies as st
import pytest

from ..forms import CardModelForm
from ..models import Number, Suit


@pytest.mark.django_db
class TestCardForm:
    @hypothesis.given(
        number=st.sampled_from(Number.values),
        suit=st.sampled_from(Suit.values),
    )
    def test_valid_form(self, number: int, suit: str):
        form_data = {"number": number, "suit": suit}
        form = CardModelForm(data=form_data)

        assert form.is_valid()

        card = form.save()
        assert card.number == number
        assert card.suit == suit

    def test_blank_data(self):
        form = CardModelForm(data={})

        assert not form.is_valid()
        assert len(form.errors) == 2

    @hypothesis.given(
        number=st.integers(min_value=14) | st.integers(max_value=0) | st.just(None),
        suit=st.sampled_from(Suit.values),
    )
    def test_invalid_number(self, number: int, suit: str):
        form_data = {"number": number, "suit": suit}
        form = CardModelForm(data=form_data)

        assert not form.is_valid()
        assert len(form.errors) == 1

    @hypothesis.given(
        number=st.integers(min_value=1, max_value=13),
        suit=st.characters(exclude_characters=Suit.values) | st.just(None),
    )
    def test_invalid_suit(self, number: int, suit: str):
        form_data = {"number": number, "suit": suit}
        form = CardModelForm(data=form_data)

        assert not form.is_valid()
        assert len(form.errors) == 1
```

元々のサンプルが単純なので、書き換える手間も少ない。
ModelとFormは似たようなテストを行っているが、エラーとなるのはModelの方だけである。
この差はどこにあるのだろうか。答えは最後の節で触れる。

ちなみに、Hypothesisは、実行するたびにテストケースが異なるので、数回テストを実行すると思わぬ発見があるかもしれない。
デフォルトではテストケース1つにつき100通りのテストを生成している。
この値は`@hypothesis.settings`デコレータで変更可能だが、生成するテスト数が多すぎるとHypothesisが遅すぎるぞ！とエラーを吐くので注意が必要である。
なお、そのエラーも抑制する方法が存在する。

### View のテスト

最後に、Viewのテストである。

```python
from django.http.response import HttpResponse
from django.urls import reverse_lazy
from django.views import generic

from .forms import CardModelForm
from .models import Card


class CardListView(generic.ListView):
    context_object_name = "card_list"
    template_name = "sample/card_list.html"
    model = Card


class CardCreateView(generic.FormView):
    form_class = CardModelForm
    template_name = "sample/card_create.html"
    success_url = reverse_lazy("sample:list")

    def form_valid(self, form: CardModelForm) -> HttpResponse:
        form.save()
        return super().form_valid(form)
```

ここまでの例だけ眺めると、「Hypothesisとpytestを使ってDjangoのユニットテストを書くのは簡単ですね、楽勝だ」と思うかもしれない。
しかし、ViewのテストをHypothesisとpytestを使って書く際に必ず陥る落とし穴が存在する。
pytestの関数スコープのfixtureとHypothesisの相性が悪いのである。
実際、Hypothesisの開発者もそれを認識しているものの、最新版のHypothesisでも同様の事象が発生する(参考: [Hypothesis works - pytest fixtures](https://hypothesis.works/articles/hypothesis-pytest-fixtures/))。

今回の場合、`pytest-django`にある`client`Fixtureが使えなくなる。
回避方法は複数あるが、`client`の場合はおとなしく`from django.test import Client`すれば回避できる。

また、Djangoとpytestを組み合わせる際に必ず登場するデコレータ`@pytest.mark.django_db`も、Hypothesisと組み合わせたViewのテストでは想定通りに機能しない疑いがある(手元で明確なエラーまでは確認できていないが、Hypothesisが1つのテストで生成する100例の間でトランザクションがどう扱われるかが不安である)。
Hypothesisを使う場合は、`hypothesis.extra.django.TestCase`に揃えたほうが安全である。
これは`django.test.TestCase`を継承しつつHypothesisとの協調を意識したクラスで、各例の間でデータベースの状態をリセットしてくれる。

それを踏まえた、落とし穴をすべて塞いだパターンのテストは以下のとおりである。

```python
import hypothesis
import hypothesis.extra.django
import hypothesis.strategies as st
from django.test import Client
from django.urls import reverse

from ..models import Card, Number, Suit


class TestCardListView(hypothesis.extra.django.TestCase):
    @hypothesis.given(
        number=st.integers(min_value=1, max_value=13),
        suit=st.sampled_from(Suit.values),
    )
    def test_card_list_view(self, number: int, suit: str):
        client = Client()
        Card.objects.create(number=number, suit=suit)

        response = client.get(reverse("sample:list"))

        assert response.status_code == 200
        assert len(response.context["card_list"]) == 1


class TestCardCreateView(hypothesis.extra.django.TestCase):
    def test_get_request(self):
        client = Client()
        response = client.get(reverse("sample:create"))

        assert response.status_code == 200

    @hypothesis.given(
        number=st.integers(min_value=1, max_value=13),
        suit=st.sampled_from(Suit.values),
    )
    def test_valid_post_request(self, number: int, suit: str):
        client = Client()
        form_data = {"number": number, "suit": suit}
        response = client.post(reverse("sample:create"), data=form_data)

        assert response.status_code == 302
        assert Card.objects.count() == 1

        card = Card.objects.first()
        assert card.number == number
        assert card.suit == suit
        assert str(card) == f"{suit}{number}"

    @hypothesis.given(
        number=st.integers(min_value=14) | st.integers(max_value=0) | st.just(""),
        suit=st.sampled_from(Suit.values),
    )
    def test_invalid_post_by_number(self, number: int, suit: str):
        client = Client()
        form_data = {"number": number, "suit": suit}
        response = client.post(reverse("sample:create"), data=form_data)

        assert response.status_code == 200
        assert Card.objects.count() == 0

    @hypothesis.given(
        number=st.integers(min_value=1, max_value=13),
        suit=st.characters(exclude_characters=Suit.values) | st.just(""),
    )
    def test_invalid_post_by_suit(self, number: int, suit: str):
        client = Client()
        form_data = {"number": number, "suit": suit}
        response = client.post(reverse("sample:create"), data=form_data)

        assert response.status_code == 200
        assert Card.objects.count() == 0
```

ここでModelやFormのテストと違い、欠損値を`None`ではなく空文字列`""`で表現している点に注意してほしい。
HTTPリクエストのフォームデータは文字列として送信されるため、ポストされる側(Viewとその先のForm)から見れば「値がない」は空文字列で届く。
`None`を渡すとHTTPクライアントのレイヤで予期しないシリアライズが起きる可能性があるため、View経由のテストでは`st.just("")`としておくのが素直である。

感覚的には、パラメータテストをさらに進化させたような感覚がある。
Hypothesisを使って「想定していませんでした」を減らせると良いなと感じている。
とはいえ、プロパティベーステストは従来のユニットテストを完全に置き換えるものではない。
今回のケースだと、`Card`生成の成功パターン、Formに空データを入れるパターンでは不要である。
境界値が曖昧なケースや想定するパターンが複雑なケースで真価を発揮するはずだ。

## もちろんフルパワーであなたと戦う気はありませんからご心配なく…

Hypothesisには他にもステートフルテストや凝ったストラテジの生成など、機能がたくさんある。
Djangoの場合、FormのテストをHypothesisで強化するところから始めると導入しやすいかもしれない。
想定していない入力をバンバンHypothesisが生成してくれるだろう。

ちなみに、pytestを実行する際に`--hypothesis-show-statistics`オプションをつけると、Hypothesisが生成したテストケースの量などがわかる。

```
test: commands[0]> pytest --hypothesis-show-statistics --hypothesis-explain .
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-8.1.1, pluggy-1.4.0
cachedir: .tox/test/.pytest_cache
Using --randomly-seed=3654462177
django: version: 5.0.4, settings: sampleproject.settings (from ini)
rootdir: /home/runner/work/my_playground/my_playground/django_playground
configfile: pytest.ini
plugins: randomly-3.15.0, Faker-24.11.0, hypothesis-6.100.1, django-4.8.0
collected 12 items

sample/tests/test_models.py ...                                          [ 25%]
sample/tests/test_views.py .....                                         [ 66%]
sample/tests/test_forms.py ....                                          [100%]
============================ Hypothesis Statistics =============================

sample/tests/test_models.py::TestCardModel::test_invalid_suit:

  - during generate phase (0.20 seconds):
    - Typical runtimes: ~ 1ms, of which < 1ms in data generation
    - 100 passing examples, 0 failing examples, 0 invalid examples

  - Stopped because settings.max_examples=100


sample/tests/test_models.py::TestCardModel::test_card_creation:

  - during generate phase (0.15 seconds):
    - Typical runtimes: ~ 1ms, of which < 1ms in data generation
    - 71 passing examples, 0 failing examples, 0 invalid examples

  - Stopped because nothing left to do


sample/tests/test_models.py::TestCardModel::test_invalid_number:

  - during generate phase (0.20 seconds):
    - Typical runtimes: ~ 1ms, of which < 1ms in data generation
    - 100 passing examples, 0 failing examples, 0 invalid examples

  - Stopped because settings.max_examples=100


sample/tests/test_views.py::TestCardCreateView::test_valid_post_request:

  - during generate phase (0.26 seconds):
    - Typical runtimes: ~ 3-4 ms, of which < 1ms in data generation
    - 56 passing examples, 0 failing examples, 0 invalid examples

  - Stopped because nothing left to do


sample/tests/test_views.py::TestCardCreateView::test_invalid_post_by_suit:

  - during generate phase (0.81 seconds):
    - Typical runtimes: ~ 6-9 ms, of which < 1ms in data generation
    - 100 passing examples, 0 failing examples, 0 invalid examples

  - Stopped because settings.max_examples=100


sample/tests/test_views.py::TestCardCreateView::test_invalid_post_by_number:

  - during generate phase (0.81 seconds):
    - Typical runtimes: ~ 6-9 ms, of which < 1ms in data generation
    - 100 passing examples, 0 failing examples, 0 invalid examples

  - Stopped because settings.max_examples=100


sample/tests/test_views.py::TestCardListView::test_card_list_view:

  - during generate phase (0.14 seconds):
    - Typical runtimes: ~ 1-2 ms, of which < 1ms in data generation
    - 56 passing examples, 0 failing examples, 0 invalid examples

  - Stopped because nothing left to do


sample/tests/test_forms.py::TestCardForm::test_invalid_suit:

  - during generate phase (0.27 seconds):
    - Typical runtimes: ~ 1-2 ms, of which < 1ms in data generation
    - 100 passing examples, 0 failing examples, 0 invalid examples

  - Stopped because settings.max_examples=100


sample/tests/test_forms.py::TestCardForm::test_invalid_number:

  - during generate phase (0.22 seconds):
    - Typical runtimes: ~ 1-2 ms, of which < 1ms in data generation
    - 100 passing examples, 0 failing examples, 0 invalid examples

  - Stopped because settings.max_examples=100


sample/tests/test_forms.py::TestCardForm::test_valid_form:

  - during generate phase (0.17 seconds):
    - Typical runtimes: ~ 1-2 ms, of which < 1ms in data generation
    - 72 passing examples, 0 failing examples, 0 invalid examples

  - Stopped because nothing left to do


============================== 12 passed in 4.02s ==============================
  test: OK (15.39=setup[9.37]+cmd[6.02] seconds)
  congratulations :) (15.45 seconds)
```

pytestのログだとテスト数が少なく思えるが、実際は各ケースごとに100回テストを行っている(はずだ)。

## OverflowError: Python int too large to convert to SQLite INTEGER の解決方法

さて、想定していない入力として、巨大な数値(具体的には、int64の範囲を超える整数)が投入されたケースはどうやって直せばよいか。
ついでに、先ほど保留した「なぜFormのテストは通ってModelのテストは失敗したのか」という疑問にも答えが出る。

### CheckConstraintは最初の防御壁にならない

CHECK制約は、データベースに設定するものである。
つまり、チェックする前にSQLiteのINTEGERの範囲を超える整数を投入されたらどうしようもない。

### Modelのバリデーション

ModelのFieldにバリデーションを設定できる。

```python
from django.core.validators import MaxValueValidator, MinValueValidator


class Card(models.Model):
    number = models.IntegerField(
        choices=Number,
        validators=(
            MaxValueValidator(Number.KING.value),
            MinValueValidator(Number.ACE.value),
        ),
    )
    suit = models.CharField(max_length=1, choices=Suit)
```

しかし、設定してもバリデーションは効かない。
何故なのか。
その秘密は[Djangoのドキュメント](https://docs.djangoproject.com/ja/5.0/ref/models/instances/#validating-objects)に書かれている。
雑に要約すると、

- Modelの`full_clean()`メソッドを使うと、モデルに設定してあるバリデーションが実行される。
- ModelFormを使っている場合、`is_valid()`メソッドを実行するとバリデーションが実行される。
- `Model`の`save()`メソッドを呼んだ際、`full_clean()`や`clean()`は自動的に呼ばれない。

つまり、`Card.objects.create()`や`card.save()`など、`Card`から直接レコードを作成すると、ModelのFieldにバリデーションが短絡されてしまう。
そのため、巨大な数値を投入された際にはCHECK制約しか機能せず、その防御壁も突破されてしまったのだ。
Modelのテストに失敗してFormのテストが通過したのは、この性質によるものだ。
Formの`is_valid()`はバリデーションをきちんと呼ぶため、巨大な数値は`MaxValueValidator`で事前にはじかれる。
一方、Modelの`Card.objects.create()`はバリデーションを呼ばないため、データベースまで値が届き、SQLiteの範囲を超えた瞬間にOverflowErrorが出る。

よって、Modelのテストを次のように書き換える。
明示的に`full_clean()`を呼ぶしかない。

```python
import hypothesis
import hypothesis.extra.django
import hypothesis.strategies as st
import pytest
from django.core.exceptions import ValidationError

from ..models import Card, Number, Suit


class TestCardModel(hypothesis.extra.django.TestCase):
    @hypothesis.given(
        number=st.integers(min_value=Number.ACE.value, max_value=Number.KING.value),
        suit=st.sampled_from(Suit.values),
    )
    def test_card_creation(self, number: int, suit: str):
        card = Card(number=number, suit=suit)
        card.full_clean()
        card.save()

        assert card.number == number
        assert card.suit == suit
        assert str(card) == f"{suit}{number}"

    @hypothesis.given(
        number=st.integers(min_value=14) | st.integers(max_value=0) | st.just(None),
        suit=st.sampled_from(Suit.values),
    )
    def test_invalid_number(self, number: int, suit: str):
        with pytest.raises(ValidationError):
            card = Card(number=number, suit=suit)
            card.full_clean()

    @hypothesis.given(
        number=st.integers(min_value=Number.ACE.value, max_value=Number.KING.value),
        suit=st.characters(exclude_characters=Suit.values) | st.just(None),
    )
    def test_invalid_suit(self, number: int, suit: str):
        with pytest.raises(ValidationError):
            card = Card(number=number, suit=suit)
            card.full_clean()
```

これで、バリデーションやCHECK制約がすべて機能する状態にできた。

## 愚かなる者よ、何故に『戦い』に身を置く？

- 何かを守るためだ
- そういう話は……興味ない
- <!-- (`choices`の存在が……)(意義がわからないから……)(こんなエントリを書いている……のかもな) -->

## まとめ

- `Choices`クラスの登場により、ModelのFieldにある`choices`を指定しやすくなった。
- しかし、`Choices`クラスを使っても、ModelのFieldにある`choices`だけでは、データベースに入る値を制限できない。
- CHECK制約を使えばデータベースに入る値を制限できる。`Choices`クラスの属性を活用することもできる。
- ただし、`Choices`クラスに`__empty__`属性を指定した場合はCHECK制約に`None`が混ざるので少し注意が必要である。
- ModelのFieldにある`choices`を指定した状態でModelFormを実装すると、期待するバリデーションを備えたFormができる。
- プロパティベーステストライブラリHypothesisで従来のテストを書き換えると、int64境界のOverflowErrorのような「想定していなかった」ケースを発見できる。
- Modelの`save()`はバリデーションを自動で呼ばないので、ModelFormを使わずに`Card.objects.create()`系でレコードを作る場合は`full_clean()`を明示的に呼ぶ必要がある。

このサンプルコード自体は何も意味のないものだが、HypothesisのおかげでDjangoのModelバリデーションの振る舞いについて少しだけ詳しくなれた。
