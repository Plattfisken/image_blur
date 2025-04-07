## Kom igång

### Dessa program behöver finnas installerade:
* Python
* pip

### Starta en virtuell miljö:
```console
python -m pip install virtualenv
virtualenv venv
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
curl -X 'POST' 'http://127.0.0.1:8000' -H "accept: application/json" -H "Content-Type: multipart/form-data" -F "images=@./Image1.jpg;type=image/jpeg" -F "images=@./Image2.jpg;type=image/jpeg" --output images.zip
```
