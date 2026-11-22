# 東吳資料科學系問答系統

## 本機啟動

使用 Python 3.10 以上。先進入本目錄。

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

瀏覽 http://127.0.0.1:5001 。未設定 `OPENAI_API_KEY` 時，網頁標示為「本機試跑」，以字詞比對顯示系網段落，不呼叫 AI API，也不需要 ChromaDB。若只需要試跑，安裝 Flask 和 python-dotenv 即可。

要啟用 OpenAI 回答時，在本目錄的 `.env` 檔將金鑰貼到 `OPENAI_API_KEY=` 後面，存檔後重新啟動程式。首次提問時會將系網段落向量化並寫入本機 `.chroma/`，其後只重建變更的段落。問題向量化及回答生成均使用 API，會按用量計費。網站刻意只監聽本機，供原型展示。

## 程式分工

| 檔案 | 職責 |
|---|---|
| `app.py` | Flask 網頁及問答 API，驗證輸入並回應請求。 |
| `sources.py` | 載入系網段落、標題及網址。 |
| `collect_sources.py` | 擷取系網正文、問答及各頁師資名單，更新本機資料。 |
| `course_tables.py` | 解析各學年度必選修科目表 PDF，並核對必修學分總計。 |
| `retrieval.py` | 建立 Chroma 向量索引、檢索相關段落，並提供本機試跑搜尋。 |
| `assistant_service.py` | 組合回答規則與檢索證據，呼叫 GPT-6 Luna，並從已知來源還原有需要的連結。 |
| `templates/`、`static/` | 網頁、樣式及瀏覽器端的問答介面。 |

目前收錄官方系網正文、專任師資與實驗室介紹。110 至 115 學年度必選修科目表 PDF 已解析為各科目的選別、學分與開課學期（`course_tables.py`），並依入學年度與年級分段；問題未指定入學年度時以最新年度回答。影片與招生文件以系網入口供查閱，尚未解析影片字幕或即時職缺名單。回答下方會列出所依據的系網段落。網頁會帶上最近三輪對話供助理理解追問，重新整理頁面會清空對話。正式招生日期或要求以官方簡章為準。

要更新系網資料，在同一個 Python 環境執行 `python collect_sources.py`，完成後重啟。
