## Kom igång

### Dessa program behöver finnas installerade:
* Python
* pip

### Starta en virtuell miljö:
```console
python -m venv .venv
source venv/bin/activate
python -m pip install --upgrade pip
```

### Installera dependencies:
```console
pip install -r requirements.txt
```

### Starta API:
```console
fastapi dev blur_api.py
```

### Exempel på request:
```console
curl -X 'POST' \
  'http://127.0.0.1:8000/enqueue?application_name=app1&application_guid=d574a738-a7a9-40f1-a4ee-8773b05b029d&blur_threshold=0.9&highlight_threshold=0.4' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'image_upload_files=@image1.jpeg;type=image/jpeg' \
  -F 'image_upload_files=@image2.jpg;type=image/jpeg'

```
