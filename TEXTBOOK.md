# ミューテーションテスト教科書の取り込み

教科書の正本は [HayaoSuzuki/hoimin の docs/book](https://github.com/HayaoSuzuki/hoimin/tree/main/docs/book) で管理する。
このリポジトリではビルド時に固定コミットから取り込み、`/mutation-testing/` に公開する。

GitHub Actionsは `.github/workflows/ci.yml` に固定したコミットを `.book-source/` にチェックアウトし、`tools/import_mutation_book.py` でコピーする。
原稿と実習コードをこのリポジトリで手編集しない。
取り込むのはGitで追跡されたファイルだけで、無視された一時ファイルは公開しない。
生成先と取り込み元はGitの追跡対象外である。

ローカルでビルドするときは、ソースの固定コミットをチェックアウトした別の作業フォルダを用意する。
次をこのリポジトリのルートから実行する。`PATH_TO_HOIMIN` は、そのフォルダのパスに置き換える。

```console
python tools/import_mutation_book.py --source PATH_TO_HOIMIN
uv run mkdocs build --strict
```

取り込みスクリプトは、ソースのoriginとHEAD、原稿に未コミットの変更がないことを確認する。
別のコミットや別リポジトリを指定した場合はコピーしない。
既存の生成先を更新するときは、固定されたパスと生成マーカーを確認したうえで置き換える。

改訂時は、hoimin側の変更をコミットしてリモートへpushしてから、ワークフローの `ref` とスクリプトの `SOURCE_REVISION` を同じ新しいSHAへ更新する。
個人サイトのPRでビルドを確認し、mainへマージすると既存のPagesワークフローが公開する。
PRの検証ビルドは公開しない。
