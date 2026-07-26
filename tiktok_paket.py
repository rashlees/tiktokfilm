#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FilmArşivi — Günlük TikTok video paketi üreteci
Her çalıştığında bir "Bugünün 5 Filmi" video paketi hazırlar:
  tiktok/BUGUN.md         → senaryo, başlık, açıklama, hashtag (kopyala-yapıştır)
  tiktok/afis/1..5.jpg    → 5 filmin afişleri (CapCut'a sürükle)
  tiktok/arsiv/<tarih>.md → geçmiş paketler saklanır (tekrar önlemek için)
Farklı tema her gün: Pazartesi aksiyon, Salı gerilim... (hafta boyu çeşitlilik)
"""
import json, os, re, sys, time, random, datetime
from urllib.request import urlopen, Request

# ==================== AYARLAR ====================
API_KEY = "4167c70c2f1823cb24e347d8a88e748b"
API     = "https://api.themoviedb.org/3"
IMG     = "https://image.tmdb.org/t/p"      # Actions ABD'de, doğrudan TMDB görseli
LANG    = "tr-TR"
SITE    = "filmarsivi"                        # video sonu çağrısı (domain alınca güncelle)

# Haftanın her günü farklı tema (çeşitlilik = daha çok izlenme)
TEMALAR = [
    # (etiket, tür_id, başlık_kalıbı, hook_cümlesi)
    ("Aksiyon",     "28",    "Nefes Kesen 5 Aksiyon Filmi",        "Adrenalin arıyorsan bu 5 film tam sana göre 👊"),
    ("Gerilim",     "53",    "Uykunu Kaçıracak 5 Gerilim Filmi",   "Sonunu tahmin edemeyeceğin 5 gerilim 😱"),
    ("Bilim Kurgu", "878",   "Aklını Uçuracak 5 Bilim Kurgu",      "Beynini yakacak 5 bilim kurgu filmi 🤯"),
    ("Komedi",      "35",    "Kahkaha Garantili 5 Komedi",         "Gününü kurtaracak 5 komedi filmi 😂"),
    ("Dram",        "18",    "Yüreğine Dokunacak 5 Dram Filmi",    "Seni benden alacak 5 dram filmi 🥲"),
    ("Korku",       "27",    "Geceleri İzlenmez 5 Korku Filmi",    "Tek başına izleme dersem? 👻"),
    ("Romantik",    "10749", "İçini Isıtacak 5 Romantik Film",     "Bu 5 filmden sonra âşık olacaksın 💘"),
]

def fetch(path, params=""):
    url = f"{API}{path}?api_key={API_KEY}&language={LANG}{params}"
    req = Request(url, headers={"User-Agent": "FilmArsivi-Bot/1.0"})
    for a in range(3):
        try:
            with urlopen(req, timeout=20) as r:
                return json.load(r)
        except Exception as e:
            if a == 2:
                print(f"UYARI: {path} alınamadı: {e}")
                return {}
            time.sleep(2)

def download(url, path):
    try:
        req = Request(url, headers={"User-Agent": "FilmArsivi-Bot/1.0"})
        with urlopen(req, timeout=20) as r, open(path, "wb") as f:
            f.write(r.read())
        return True
    except Exception as e:
        print(f"UYARI: afiş inmedi {url}: {e}")
        return False

def load_used():
    try:
        with open("tiktok/kullanilanlar.json", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_used(used):
    with open("tiktok/kullanilanlar.json", "w", encoding="utf-8") as f:
        json.dump(sorted(used), f)

def pick_films(genre_id, used, test=False):
    if test:
        return [
            {"id": 1, "title": "Örnek Film Bir", "vote_average": 8.2, "release_date": "2024-01-01",
             "overview": "Kısa çarpıcı bir konu cümlesi burada yer alır.", "poster_path": "/a.jpg"},
            {"id": 2, "title": "Örnek Film İki", "vote_average": 7.9, "release_date": "2023-05-01",
             "overview": "İkinci filmin merak uyandıran konusu.", "poster_path": "/b.jpg"},
            {"id": 3, "title": "Örnek Film Üç", "vote_average": 7.7, "release_date": "2022-08-01",
             "overview": "Üçüncü film hakkında kısa bilgi.", "poster_path": "/c.jpg"},
            {"id": 4, "title": "Örnek Film Dört", "vote_average": 7.5, "release_date": "2021-03-01",
             "overview": "Dördüncü filmin özeti.", "poster_path": "/d.jpg"},
            {"id": 5, "title": "Örnek Film Beş", "vote_average": 7.4, "release_date": "2020-11-01",
             "overview": "Beşinci filmin kısa tanıtımı.", "poster_path": "/e.jpg"},
        ]
    films = []
    # Rastgele sayfa: her gün farklı filmler gelsin
    for page in random.sample(range(1, 8), 4):
        d = fetch("/discover/movie",
                  f"&with_genres={genre_id}&sort_by=vote_average.desc"
                  f"&vote_count.gte=800&page={page}&without_genres=99,10755")
        for f in d.get("results", []):
            if (f.get("id") not in used and f.get("poster_path") and f.get("overview")
                    and f.get("vote_average", 0) >= 6.5):
                films.append(f)
        if len(films) >= 20:
            break
    random.shuffle(films)
    return films[:5]

def build():
    test = "--test" in sys.argv
    os.makedirs("tiktok/afis", exist_ok=True)
    os.makedirs("tiktok/arsiv", exist_ok=True)

    today = datetime.date.today()
    tema = TEMALAR[today.weekday()]   # 0=Pazartesi
    etiket, gid, baslik, hook = tema
    used = load_used()

    films = pick_films(gid, used, test)
    if len(films) < 5:
        print("UYARI: yeterli film bulunamadı, kullanılanlar sıfırlanıyor")
        used = set()
        films = pick_films(gid, used, test)
    films = films[:5]

    # Afişleri indir + senaryo satırları üret
    lines, captions = [], []
    for i, f in enumerate(films, 1):
        title = f.get("title") or ""
        year = (f.get("release_date") or "")[:4]
        rating = f'{f.get("vote_average", 0):.1f}'
        ov = (f.get("overview") or "").strip()
        # Kısa, tempolu konu (ilk cümle)
        short = re.split(r"(?<=[.!?])\s", ov)[0]
        if len(short) > 90:
            short = short[:87] + "..."
        if not test:
            download(f"{IMG}/w500{f['poster_path']}", f"tiktok/afis/{i}.jpg")
        used.add(f.get("id"))
        lines.append(f"{i}️⃣ {title} ({year}) — ⭐ {rating}\n     {short}")
        captions.append(f"{i}. {title}")

    if not test:
        save_used(used)

    tarih_tr = today.strftime("%d.%m.%Y")
    hashtags = ("#film #filmönerisi #dizi #netflix #filmtavsiyesi #izlenmesigerekenfilmler "
                f"#{etiket.lower().replace(' ','')} #filmarşivi #sinema #keşfet #fyp #keşfetteyiz")

    senaryo = f"""# 🎬 BUGÜNÜN VİDEOSU — {tarih_tr}
## Tema: {etiket} · "{baslik}"

---

## 📱 CAPCUT'TA NE YAPACAKSIN (5 dk)
1. `tiktok/afis/` klasöründeki 1-2-3-4-5.jpg afişlerini sırayla ekle (her biri ~3 sn)
2. Her afişin üstüne aşağıdaki METNİ yaz (kopyala-yapıştır)
3. Trend bir müzik seç (CapCut → Ses → Trend)
4. Başlığı en başa 1 sn "kapak" olarak koy: **{baslik}**
5. Videoyu indir, TikTok/Reels/Shorts'a yükle

---

## 🎞️ EKRAN METİNLERİ (afişlerin üstüne)

**KAPAK (ilk kare):**
{baslik} 🍿

**Açılış sözü (sesli/yazılı):**
{hook}

{chr(10).join(lines)}

**KAPANIŞ (son kare):**
Hangisini izledin? 👇 Tam liste ve "nerede izlenir" bilgisi → {SITE}

---

## ✍️ TIKTOK AÇIKLAMASI (kopyala-yapıştır)
{baslik} 🎬 Kaydet, unutma!
{" · ".join(captions)}
Tam liste ve nerede izleneceği profildeki linkte 🔗
{hashtags}

---

## 💡 İPUCU
- İlk 1 saniye kritik: kapak yazısı büyük ve merak uyandırıcı olsun
- Sesli anlatım eklersen izlenme 2-3 kat artar (telefon mikrofonu yeter)
- Günde 1, haftada en az 4-5 video = algoritma seni sever
- Aynı videoyu TikTok + Instagram Reels + YouTube Shorts'a at (3 kat erişim)
"""

    with open("tiktok/BUGUN.md", "w", encoding="utf-8") as f:
        f.write(senaryo)
    # Arşive de kopyala
    with open(f"tiktok/arsiv/{today.isoformat()}-{etiket}.md", "w", encoding="utf-8") as f:
        f.write(senaryo)

    print(f"BİTTİ: {etiket} teması, {len(films)} film")
    print(f"  → tiktok/BUGUN.md (senaryo)")
    print(f"  → tiktok/afis/1-5.jpg (afişler)")
    for c in captions:
        print(f"     {c}")

if __name__ == "__main__":
    build()
