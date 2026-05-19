# Frizbi: Çok Ajanlı (Multi-Agent) Otonom B2B Trend Analiz ve Mağaza Otomasyon Sistemi

Frizbi, internet üzerindeki canlı sosyal sinyalleri (Reddit, e-ticaret forumları vb.) ve kurumsal B2B pazar yerlerini (Alibaba) uçtan uca otonom olarak tarayan, analiz eden ve doğrulanmış trend ürünleri anında dijital mağazaya aktaran **LangGraph** tabanlı bir yapay zeka orkestrasyon sistemidir.

## 🌟 Temel Mimari Özellikler

- **LangGraph Döngüsel Graf Yapısı:** Durum yönetimli (Stateful), çok ajanlı mimari sayesinde kararlar deterministik kurallara bağlı kalmaksızın esnek yapay zeka düğümleri tarafından verilir.
- **Kurumsal Veri Entegrasyonu (Bright Data Scraper API):** Siber güvenlik duvarları (Akamai, Cloudflare) ve karmaşık dinamik DOM yapıları, kurumsal düzeyde veri hatları üzerinden %100 captcha-safe ve asenkron polling (HTTP 202/Snapshot) mekanizmalarıyla aşılır.
- **Gelişmiş RAG Katmanı (ChromaDB):** Pazar yerlerinden çekilen ham ürün açıklamaları ve ticari alıcı yorumları anlık olarak anlamsal parçalara (chunks) ayrılarak lokal vektör veritabanında indekslenir.
- **Toplu İroni ve Manipülasyon Analizi (LLM Guard):** Ürünlerin güvenilirlik skorları hesaplanırken, tedarikçilerin yapay bot yorumları veya alaycı alıcı geri bildirimleri tek bir LLM çağrısıyla toplu (batching) anlamsal süzgeçten geçirilir.

## 🤖 Yapay Zeka Ajanları (Agents) ve Görevleri

1. **Trend Agent:** Reddit JSON akışlarından canlı trend sinyallerini toplar ve Gemini LLM yardımıyla kullanıcı talebini en yüksek dönüşüm oranlı küresel İngilizce arama terimlerine genişletir.
2. **Product Hunter Agent:** Bright Data altyapısı üzerinden B2B pazar yerini tetikler. Çekilen ham fiyatları akıllı matematiksel süzgeçten geçirerek USD para birimine normalize eder; minimum sipariş miktarı (MOQ) ve tedarikçi puanına göre bilesik viabilite skoru hesaplar.
3. **Content Agent:** Skorlanmış ham B2B verilerini satış odaklı, Türkçe SEO uyumlu özgün ürün başlıklarına ve meta açıklamalarına dönüştürür.
4. **Operations Agent:** Birim tedarik maliyetlerini referans alarak lojistik süre sınırlarını hesaplar ve yerel pazar çarpanlarına göre ideal Türkiye satış fiyatlamasını otomatik kurgular.
5. **Orchestrator Review (Baş Ajan):** Tüm ajanların çıktılarını bütünlük ve veri doğruluğu testine tabi tutar. Vektör veritabanından gelen yorumları ironi/troll süzgecinden geçirerek güvenilirlik skoru 70'in altında kalan kusurlu ürünleri sistemden eler veya süreci güvenli "Retry" döngüsüne sokar.

## 📦 Kurulum ve Çalıştırma

### 1. Bağımlılıkların Yüklenmesi
Sanal ortamınızı aktif ettikten sonra gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt