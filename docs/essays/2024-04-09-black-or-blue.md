# 黒か、青か

*2024-04-09 公開*

先日、[blue](https://github.com/grantjenks/blue)なるコードフォーマッタの存在を知った。
blueはLinkedInの従業員が[Black](https://github.com/psf/black)に影響されて作ったフォーマッタのようである。
README.mdに興味深い記述がある。

> blue defaults to single-quoted strings. This is probably the most painful black choice to our eyes, and the thing that inspired blue. We strongly prefer using single quoted strings over double quoted strings for everything except docstrings and triple quoted strings (TQS). Don't ask us why we prefer double-quotes for TQS; it just looks better to us! For all other strings, blue defaults to single quoted strings. In the case of docstrings, those always use TQS with double-quotes.

"This is probably the most painful black choice to our eyes" とは思い切った記述である。
Pythonでは単一引用符と二重引用符は等価なので、意味論上はどちらを使っても違いはない。
それにもかかわらず、二重引用符に対してここまでの感情を抱いているのが気になる。
穿鑿したところで意味はないのだが、それでも自分なりに想像を試みる。

私が思いついたのは、キーボード配列の違いではないかという仮説である。
USキーボードの場合、単一引用符と二重引用符は同一のキーに割り当てられている。
単一引用符はそのキーを打鍵すればよいが、二重引用符の場合は左手でシフトキーを押しながら打鍵する必要がある。
つまり、二重引用符のほうが1手余計にかかる。
コードを書いていれば文字列リテラルは頻出するので、その都度シフトキーを押すのが確かに億劫に感じられてもおかしくない。
一方、JISキーボードでは単一引用符も二重引用符も数値キー上にあり、いずれもシフトキーを押す必要があるため手数に差はない。

ちなみに、私はJISキーボードを愛用している。
というより、USキーボードが使えない。
また、シフトキーは右手小指で押す癖があり、右手小指でシフトを押しながら左手中指で二重引用符を入力している。
つまり、私にとってはむしろ二重引用符のほうが打鍵しやすく、Blackのフォーマットに違和感を感じないのは、単にその恩恵を受けていないからだろう。

もう1つ考えたのは、他言語からの影響という仮説である。
[PHP](https://www.php.net/manual/ja/language.types.string.php)や[Ruby](https://docs.ruby-lang.org/ja/latest/doc/spec=2fliteral.html#string)では、単一引用符と二重引用符で文字列リテラルの動作が異なる。
単一引用符はエスケープも変数展開もしない、ただの文字列リテラルである。
二重引用符はエスケープシーケンスを解釈し、変数展開も行う。
PHPユーザやRubyユーザならば余計なことをしない単一引用符をデフォルトとして使う文化が根付きやすい。
Pythonにその感覚を持ち込もうとするならば、違和感なく馴染むのはblueのような単一引用符優先のフォーマッタだろう。

とはいえ、いずれも自転車置き場の議論の域を出ない。
[PEP 8](https://peps.python.org/pep-0008/#a-foolish-consistency-is-the-hobgoblin-of-little-minds)にも次のような記述がある。

> A style guide is about consistency. Consistency with this style guide is important. Consistency within a project is more important. Consistency within one module or function is the most important.

結局、プロジェクトで何らかの合意が取れていれば、何色でもそれでいいのである。
そしてBlackは、その「合意」の部分を徹底的にツールに委ね、個人の好みが入る余地を排除した。
だからこそプロジェクトに導入しやすくなり、Blackが流行しているのだと、私は推測している。
