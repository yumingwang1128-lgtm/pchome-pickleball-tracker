# PChome 匹克球拍價格追蹤

此專案保存 PChome 公開商品頁的價格快照，供教學與市場趨勢分析使用。MVP 僅追蹤名稱含「匹克球拍」的商品，不將球、球套與場地配件混入價格統計。

## 資料欄位

必要欄位：商品 ID、名稱、URL、搜尋詞、現價、幣別、擷取時間。可空欄位：原價、品牌、評分、評價數與庫存狀態。`NULL` 不等於 0，表示公開頁面沒有提供資料。

## 安全使用

自動網路請求預設關閉。先自行確認 PChome 的適用條款、robots 規則與資料使用範圍，再用下列指令手動啟用；每個請求至少間隔兩秒，第一次最多收集 10 項商品。

```powershell
$env:PYTHONPATH = 'src'
python -m pickleball_tracker.cli --live --max-products 10
```

不要把資料取得憑證寫進程式碼或 Git repository。GitHub Actions 會在每天台灣時間 09:00 執行，也可手動觸發；它會在測試與收集成功後，將更新的 `data/tracker.db` 提交回預設分支。首次推送到 GitHub 後，請在 Actions 頁面手動執行一次並確認結果。

## 本機驗證與儀表板

```powershell
python -m unittest discover -s tests -v
pip install -r requirements.txt
streamlit run app.py
```
