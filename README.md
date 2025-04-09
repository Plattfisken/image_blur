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
  'http://127.0.0.1:8000/?threshold=0.8' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'image_files=@img1.jpg;type=image/jpeg' \
  -F 'image_files=@img2.jpg;type=image/jpeg'
```
