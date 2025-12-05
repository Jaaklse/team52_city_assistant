import requests
import time
from datetime import datetime, timedelta

def get_page(page_number, count=100):
    """
    Получить одну страницу данных
    """
    url = "https://yazzh.gate.petersburg.ru/beautiful_places/"
    
    params = {
        'page': page_number,
        'count': count
    }
    
    headers = {
        'accept': 'application/json',
        'region': '78'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  
        return response.json()
    except Exception as e:
        print(f"Ошибка при запросе страницы {page_number}: {e}")
        return None

def get_afisha_data(page=1, count=10, days_ahead=14):
    """
    Получить данные с афиши событий на актуальные 2 недели вперед
    """
    today = datetime.now()
    start_date = today.strftime('%Y-%m-%dT00:00:00')
    end_date = (today + timedelta(days=days_ahead)).strftime('%Y-%m-%dT00:00:00')
    
    url = "https://yazzh.gate.petersburg.ru/afisha/all/"
    
    params = {
        'start_date': start_date,
        'end_date': end_date,
        'page': page,
        'count': count
    }
    
    headers = {
        'accept': 'application/json',
        'region': '78'
    }
    
    try:
        print(f"Получаем афишу (страница {page}) с {start_date} по {end_date}...")
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Ошибка при получении афиши: {e}")
        return None

def get_all_afisha_events(count_per_page=10):
    """
    Получить все события афиши с учетом общего количества
    """
    all_events = []
    
    first_page_data = get_afisha_data(page=1, count=count_per_page)
    
    if not first_page_data:
        print("Не удалось получить данные афиши")
        return all_events
    
    total_count = first_page_data.get('count', 0)
    print(f"Всего событий в афише: {total_count}")
    

    if 'data' in first_page_data:
        all_events.extend(first_page_data['data'])
        print(f"Получено {len(first_page_data['data'])} событий с страницы 1")
    
    total_pages = (total_count + count_per_page - 1) // count_per_page
    
    for page in range(2, total_pages + 1):
        print(f"Получаем страницу афиши {page}...")
        
        page_data = get_afisha_data(page=page, count=count_per_page)
        
        if page_data and 'data' in page_data:
            events_on_page = page_data['data']
            all_events.extend(events_on_page)
            print(f"Получено {len(events_on_page)} событий")
        else:
            print(f"Страница {page} пуста или ошибка")
            break
        
        time.sleep(0.3)
    
    return all_events

def save_afisha_to_file(events, filename="afisha_events.txt"):
    """
    Сохранить данные афиши в файл
    """
    if not events:
        print("Нет данных афиши для сохранения")
        return
    
    with open(filename, 'w', encoding='utf-8') as f:
        for i, event_info in enumerate(events, 1):
            place = event_info.get('place', {})
            
            categories = place.get('categories', [])
            categories_str = ', '.join(categories) if categories else 'Не указано'
            
            start_date = place.get('start_date', 'Не указано')
            end_date = place.get('end_date', 'Не указано')
            
            if start_date != 'Не указано':
                try:
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    start_date_formatted = start_dt.strftime('%Y-%m-%d %H:%M')
                except:
                    start_date_formatted = start_date
            
            if end_date != 'Не указано':
                try:
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    end_date_formatted = end_dt.strftime('%Y-%m-%d %H:%M')
                except:
                    end_date_formatted = end_date
            
            f.write(f"Запись {i}\n")
            f.write(f"Название: {place.get('title', 'Не указано')}\n")
            f.write(f"Описание: {place.get('description', 'Не указано')}\n")
            f.write(f"Дата начала: {start_date_formatted if 'start_date_formatted' in locals() else start_date}\n")
            f.write(f"Дата окончания: {end_date_formatted if 'end_date_formatted' in locals() else end_date}\n")
            f.write(f"Возрастное ограничение: {place.get('age', 'Не указано')}\n")
            f.write(f"Категория: {categories_str}\n")
            f.write(f"Название локации: {place.get('location_title', 'Не указано')}\n")
            f.write(f"Адрес: {place.get('address', 'Не указано')}\n")
            f.write("-" * 50 + "\n\n")
    
    print(f"Данные афиши сохранены в файл {filename}")

def save_to_file(places, filename="beautiful_places.txt"):
    """
    Сохранить данные в файл
    """
    with open(filename, 'w', encoding='utf-8') as f:
        for i, place_info in enumerate(places, 1):
            place = place_info.get('place', {})
            
            f.write(f"Запись {i}\n")
            f.write(f"Название: {place.get('title', '')}\n")
            f.write(f"Описание: {place.get('description', '')}\n")
            f.write(f"Район: {place.get('district', '')}\n")
            f.write(f"Адрес: {place.get('address', '')}\n")
            
            categories = place.get('categories', [])
            categories_str = ', '.join(categories)
            f.write(f"Категории: {categories_str}\n")
            f.write(f"Ссылка: {place.get('data_source', '')}\n")
            f.write("-" * 50 + "\n\n")

def get_all_places(start_page=1, num_pages=7, count_per_page=100):
    """
    Получить все места с нескольких страниц
    """
    all_places = []
    
    for page in range(start_page, start_page + num_pages):
        print(f"Получаем страницу {page}...")
        
        data = get_page(page, count_per_page)
        
        if data and 'data' in data:
            places_on_page = data['data']
            all_places.extend(places_on_page)
            print(f"Получено {len(places_on_page)} мест")
        else:
            print(f"Страница {page} пуста или ошибка")
            break
        
        time.sleep(0.3)
    
    return all_places

def get_mfc_data():
    """
    Получить информацию о МФЦ
    """
    url = "https://yazzh.gate.petersburg.ru/mfc/all/"
    
    headers = {
        'accept': 'application/json',
        'region': '78'
    }
    
    try:
        print("\nПолучаем информацию о МФЦ...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Ошибка при получении данных о МФЦ: {e}")
        return None

def save_mfc_to_file(mfc_data, filename="mfc_info.txt"):
    """
    Сохранить информацию о МФЦ в файл
    """
    if not mfc_data or 'data' not in mfc_data:
        print("Нет данных о МФЦ для сохранения")
        return
    
    with open(filename, 'w', encoding='utf-8') as f:
        for i, mfc in enumerate(mfc_data['data'], 1):
            f.write(f"Запись {i}\n")
            f.write(f"Название: {mfc.get('name', '')}\n")
            f.write(f"Адрес: {mfc.get('address', '')}\n")
            f.write(f"Время работы: {mfc.get('working_hours', '')}\n")
            
            accessible_env = mfc.get('accessible_env', [])
            accessible_str = ', '.join(accessible_env) if accessible_env else 'Нет информации'
            f.write(f"Доступность: {accessible_str}\n")
            
            link = mfc.get('link', '')
            f.write(f"Ссылка: {link}\n")
            
            nearest_metro = mfc.get('nearest_metro', '')
            if nearest_metro:
                f.write(f"Ближайшее метро: {nearest_metro}\n")
            
            phone = mfc.get('phone', [])
            if phone:
                phone_str = ', '.join(phone)
                f.write(f"Телефон: {phone_str}\n")
            
            f.write("-" * 50 + "\n\n")

def main():
    """
    Основная функция для получения данных
    """
    print("=" * 50)
    print("Получение данных о красивых местах...")
    print("=" * 50)
    all_places = get_all_places(start_page=1, num_pages=7, count_per_page=100)
    
    if all_places:
        save_to_file(all_places, "beautiful_places.txt")
        print(f"\nВсего получено {len(all_places)} красивых мест")
        print("Данные сохранены в файл beautiful_places.txt")
    else:
        print("Не удалось получить данные о красивых местах")
    
    print("\n" + "=" * 50)
    print("Получение данных с афиши событий...")
    print("=" * 50)
    afisha_events = get_all_afisha_events(count_per_page=10)
    
    if afisha_events:
        save_afisha_to_file(afisha_events, "afisha_events.txt")
        print(f"\nВсего получено {len(afisha_events)} событий из афиши")
        print("Данные афиши сохранены в файл afisha_events.txt")
    else:
        print("Не удалось получить данные афиши")
    
    print("\n" + "=" * 50)
    print("Получение информации о МФЦ...")
    print("=" * 50)
    mfc_data = get_mfc_data()
    
    if mfc_data:
        save_mfc_to_file(mfc_data, "mfc_info.txt")
        print(f"Получено {len(mfc_data['data'])} МФЦ")
        print("Данные о МФЦ сохранены в файл mfc_info.txt")
    else:
        print("Не удалось получить данные о МФЦ")

if __name__ == "__main__":
    main()