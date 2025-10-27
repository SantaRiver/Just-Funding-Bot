"""Скрипт для исправления ошибки Telegram Conflict."""
import os
import sys
import time
import requests
from dotenv import load_dotenv

def main():
    print("🔧 Исправление конфликта Telegram Bot...")
    print()
    
    # Загружаем .env
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не найден в .env")
        sys.exit(1)
    
    print(f"✅ Токен найден: {token[:10]}...")
    print()
    
    # Проверяем webhook
    print("📋 Проверка webhook...")
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")
        webhook_info = response.json()
        
        if webhook_info.get("ok"):
            webhook_url = webhook_info.get("result", {}).get("url", "")
            
            if webhook_url:
                print(f"   ⚠️  Обнаружен webhook: {webhook_url}")
                print("   🔧 Удаляю webhook...")
                
                delete_response = requests.get(
                    f"https://api.telegram.org/bot{token}/deleteWebhook",
                    params={"drop_pending_updates": True}
                )
                delete_result = delete_response.json()
                
                if delete_result.get("ok"):
                    print("   ✅ Webhook успешно удален")
                else:
                    print(f"   ❌ Не удалось удалить webhook: {delete_result}")
            else:
                print("   ✅ Webhook не установлен")
        else:
            print(f"   ❌ Ошибка API: {webhook_info}")
    except Exception as e:
        print(f"   ❌ Ошибка при проверке webhook: {e}")
    
    print()
    
    # Очищаем pending updates
    print("📋 Очистка pending updates...")
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": -1, "timeout": 1}
        )
        print("   ✅ Pending updates очищены")
    except Exception as e:
        print(f"   ⚠️  Ошибка: {e}")
    
    print()
    
    # Ждем
    print("📋 Ожидание освобождения подключений...")
    for i in range(1, 11):
        print(f"   Попытка {i}/10...")
        time.sleep(1)
    print("   ✅ Готово")
    
    print()
    print("✅ Все проверки завершены!")
    print()
    print("💡 Теперь запустите бота:")
    print("   python bot.py")
    print()
    print("Если ошибка повторяется:")
    print("   1. Проверьте что бот не запущен на другом сервере/компьютере")
    print("   2. Проверьте что нет других процессов python bot.py")
    print("   3. Подождите 1-2 минуты и попробуйте снова")
    print("   4. Проверьте нет ли у вас webhook на хостинге (Heroku, Railway и т.д.)")

if __name__ == "__main__":
    main()
