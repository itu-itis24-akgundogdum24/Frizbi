import os
import chromadb
from datetime import datetime

def main():
    print("=" * 65)
    print("      Frizbi - ChromaDB Canlı RAG Parçaları Denetimi")
    print("=" * 65)

    db_path = os.path.join(os.getcwd(), "chroma_db")
    
    if not os.path.exists(db_path):
        print(f"[ERROR] ChromaDB dizini bulunamadi: {db_path}")
        return

    try:
        client = chromadb.PersistentClient(path=db_path)
        collections = client.list_collections()

        if not collections:
            print("[WARN] Veritabaninda henüz hicbir koleksiyon yok.")
            return

        for col in collections:
            db_content = col.get(include=["metadatas", "documents"])
            ids = db_content.get("ids", [])
            metadatas = db_content.get("metadatas", [])
            documents = db_content.get("documents", [])
            
            print(f"\n[KOLEKSİYON] İsim: {col.name} | Toplam Vektör: {len(ids)}")
            print("-" * 65)

            for i in range(len(ids)):
                meta = metadatas[i] if i < len(metadatas) else {}
                doc = documents[i] if i < len(documents) else ""
                
                # ID tipine göre (desc/review) ajanın neyi kaydettiğini jüriye gösteriyoruz
                chunk_type = "ÜRÜN AÇIKLAMASI" if "_desc_" in ids[i] else "MÜŞTERİ YORUMU"
                if "_review_" in ids[i]:
                    chunk_type = "MÜŞTERİ YORUMU"
                
                print(f"📍 [KAYIT #{i+1:02d}] [{chunk_type}]")
                print(f"  • Oturum (Session) ID : {meta.get('session_id', 'Genel Bilgi')}")
                print(f"  • Vektör Metin İçeriği: {doc.strip()}")
                print("  " + "." * 60)
            
            print("\n" + "=" * 65)

    except Exception as exc:
        print(f"[ERROR] Veritabanı okunurken hata olustu: {str(exc)}")

if __name__ == "__main__":
    main()