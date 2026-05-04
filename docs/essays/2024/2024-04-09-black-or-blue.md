# 黒か、青か

*2024-04-09 公開*

先日、[blue](https://github.com/grantjenks/blue)なるコードフォーマッタの存在を知った。
blueはLinkedInの従業員が[Black](https://github.com/psf/black)に影響されて作ったフォーマッタのようである。
README.mdに興味深い記述がある。

> blue defaults to single-quoted strings. This is probably the most painful black choice to our eyes, and the thing that inspired blue. We strongly prefer using single quoted strings over double quoted strings for everything except docstrings and triple quoted strings (TQS). Don't ask us why we prefer double-quotes for TQS; it just looks better to us! For all other strings, blue defaults to single quoted strings. In the case of docstrings, those always use TQS with double-quotes.

"This is probably the most painful black choice to our eyes" とは思い切った記述である。
Pythonでは単一引用符と二重引用符は等価で、意味論上の違いはない。
それにもかかわらず、なぜ二重引用符にこれほど強い感情が向けられるのだろうか。
穿鑿しても意味はないが、それでも自分なりに想像してみたい。

私が思いついたのは、キーボード配列の違いに起因するという仮説である。
USキーボードでは単一引用符と二重引用符が同一のキーに割り当てられている。
単一引用符はそのキーを打鍵すればよいが、二重引用符は左手でシフトキーを押しながら打鍵する必要がある。
つまり、二重引用符のほうが1手多い。
コードを書いていれば文字列リテラルは頻出するため、その都度シフトキーを押すのが億劫に感じられても不思議ではない。
一方、JISキーボードでは単一引用符も二重引用符も数値キー上にあり、どちらもシフトキーを押す必要があるため、手数に差はない。

もう1つの仮説は、他言語からの影響である。
たとえば、[PHP](https://www.php.net/manual/ja/language.types.string.php)や[Ruby](https://docs.ruby-lang.org/ja/latest/doc/spec=2fliteral.html#string)では、単一引用符と二重引用符で文字列リテラルの動作が異なる。
単一引用符はエスケープも変数展開もしない、ただの文字列リテラルである。
二重引用符はエスケープシーケンスを解釈し、変数展開も行う。
余計な処理をしない単一引用符をデフォルトとして使う文化からPythonにやってきたのであれば、意味論的に同一であっても単一引用符を使うであろう。

とはいえ、ここまでの議論は結局のところ自転車置き場の議論に過ぎない。
コードスタイルに対する議論を行わないためにBlackのようなツールを選択するのである。
