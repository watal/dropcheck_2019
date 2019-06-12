# dropcheck_2019
Let's Dropcheck !!!  
* macOS（バージョン10.14.4で動作確認済）  
* Python3系（3.7.3で動作確認済）

## 準備
### 各種インストール
```
$ brew install mtr tmux 
$ pip install -r requirements.txt
```
### config準備
```
$ cp config.yml.sample config.yml
$ vi config.yml //config.ymlにDNSサーバの情報を記入
```

## 構成

### dropcheck.sh
後述の`dropcheck_tmuxp.yml`を呼び出すスクリプトです。  
無線インターフェースが有効化されていた場合、無効にしてくれます。

`sudo dropcheck.sh`で実行してください。

### dropcheck_tmux.yml
tmuxpを用い、Dropcheck用の画面を作成します。  
単体実行：`sudo tmuxp load dropcheck_tmux.yml`

### dropcheck_report.py
全コマンドを実行し、`dat/dropcheck_report.json`に履歴を保存します。  
単体実行：`sudo dropcheck_report.py`
