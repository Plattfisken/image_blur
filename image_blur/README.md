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

## Dokumentation
API:et exponerar tre endpoints:
* [**/enqueue**](#enqueue) - Skapa ett ärende med en eller flera bilder. Ärenden kommer läggas i en kö och hanteras vid sin tur.
* [**/result**](#result) - Kolla om ett ärende är färdigt; om det är det så får du tillbaka ett resultat, annars får du ett svar som säger att det inte är färdigt ännu.
* [**/blur_rects_in_image**](#blur_rects_in_image) - Specificera rektanglar att sudda ut ur en bild. Du får tillbaka bilden med de specificerade rektanglarna utsuddade.

Alla endpoints tar emot dessa query parametrar:
* application_name: Namn på applikationen som utfärdar ärendet.
* application_guid: GUID som APIet matchar mot de tillåtna applikationerna (specificeras just nu i auth_test_data.json)

### /enqueue
Tar även emot följande:
* blur_threshold: decimalvärde mellan 0-1 som representerar gränsen på säkerhet som krävs av modellen för att _sudda ut_ en rektangel.
* highlight_threshold: decimalvärde mellan 0-1 som representerar gränsen på säkerhet som krävs av modellen för att _markera_ en rektangel. Måste vara lägre än _blur_threshold_.
* image_upload_files: En eller flera bildfiler som kommer analyseras.

Denna endpoint lägger ett ärende i en kö. Ärendet kommer automatiskt hanteras när det ligger först i kön. Vid lyckad request får man tillbaka en GUID som sedan kan användas för att hämta ut resultatet. Bilderna kommer analyseras av en objektdetekterande AI-model. Resultat där modellen tror sig se en människa med en säkerhet högre än _blur_threshold_ kommer suddas ut. De resultat med en säkerhet högre än _highlight_threshold_ men lägre än _blur_threshold_ kommer istället en grön rektangel markera var på bilden människan detekterades, och koordinaterna kommer skrivas till en separat fil. Resultat med säkerhet under _highlight_threshold_ ignoreras. När ärendet har hanterats kommer resultatet sparas på disk och ligga kvar i en vecka innan det tas bort.

Ett request kan exempelvis se ut såhär:
```console
curl -X 'POST' \
  'http://127.0.0.1:8000/enqueue?application_name=app1&application_guid=d574a738-a7a9-40f1-a4ee-8773b05b029d&blur_threshold=0.9&highlight_threshold=0.4' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'image_upload_files=@image1.jpeg;type=image/jpeg' \
  -F 'image_upload_files=@image2.jpg;type=image/jpeg'

```

### /result
Tar även emot följande:
* request_guid: GUID som har returnerats från en tidigare fråga till _/enqueue_.

Denna endpoint returnerar ett lyckat ärende i form av en zipfil. Om ärendet inte ännu har hanterats returneras istället ett meddelande som berättar just det.

När zipfilen extraheras så kommer den innehålla dessa mappar:
* result: Innehåller alla bilder som har hanterats. I bilderna är människor utsuddade om modellen gav en säkerhet som var högre än _blur_threshold_. Bilderna heter samma sak som namnen på filerna som skickades in.
* highlighted_images_for_manual_review: Innehåller de bilder där modellen gav tillbaka minst ett resultat där den tror det finns en människa med en säkerhet emellan _blur_threshold_ och _highlight_threshold_. Tillsammans med en korresponderande textfil som innehåller de markerade rektanglarnas koordinater som kommaseparerade värden (left, top, right, bottom). Varje rad i filen är en egen rektangel. Filen heter samma sak som bildfilen, fast ändelsen har byts ut mot _.txt_ och kan exempelvis se ut såhär:
```
117.48514556884766,35.16618347167969,226.17103576660156,159.22821044921875
15.584417343139648,25.157556533813477,81.97242736816406,176.9916534423828
454.3403015136719,0.4002394676208496,474.0133972167969,265.3711853027344
435.0771179199219,2.545517683029175,473.97808837890625,263.7992248535156
```
* unhandled_files_invalid_format: Innehåller de filer som inte kunde öppnas som bildfiler. Filerna heter samma sak som namnet på filerna som skickades in.
* unhandled_files_too_large: Innehåller de filer som överskrider storleksgränsen som är satt till 50MB. Filerna heter samma sak som namnet på filerna som skickades in.

Ett request kan exempelvis se ut såhär:
```console
curl -X 'GET' \
  'http://127.0.0.1:8000/result?application_name=app1&application_guid=d574a738-a7a9-40f1-a4ee-8773b05b029d&request_guid=9024c47faabb4ddd8aa61475b129f969' \
  -H 'accept: application/json'
```

### /blur_rects_in_image
Tar även emot följande:
* rect_file: Textfil med koordinater som kommaseparerade värden. Varje rad innehåller fyra värden som representerar en rektangel (left, top, right, bottom)
* image_file: En bildfil där de rektanglar som specificeras i _rect_file_ kommer suddas ut.

Denna endpoint kommer direkt sudda ut rektanglarna och sedan returnera bilden. _rect_file_ har samma format som filerna som innehåller koordinater ifrån ett lyckat ärende.

Ett request kan exempelvis se ut såhär:
```console
curl -X 'POST' \
  'http://127.0.0.1:8000/blur_rects_in_image?application_name=app1&application_guid=d574a738-a7a9-40f1-a4ee-8773b05b029d' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'rect_file=@test4.txt;type=text/plain' \
  -F 'image_file=@test4.jpg;type=image/jpeg'
```
