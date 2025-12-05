import requests
from bs4 import BeautifulSoup
import re

def clean_text(text):
    """Очищает текст от лишних пробелов, табуляций и переносов строк"""
    if not text:
        return ""
    cleaned = re.sub(r'\s+', ' ', text)
    return cleaned.strip()

def save_to_text_file(results, filename):
    """Сохраняет результаты в текстовый файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        for i, result in enumerate(results, 1):
            f.write(f"=== Запись {i} ===\n")
            f.write(f"Название: {result['Название']}\n")
            f.write(f"Описание: {result['Описание']}\n")
            f.write(f"Основная часть: {result['Основная_часть']}\n")
            f.write(f"URL: {result['URL']}\n")
            f.write("\n")

def parse_all_themes():
    """Парсит все темы из файла themes.txt"""
    
    try:
        with open('themes.txt', 'r', encoding='utf-8') as f:
            themes = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("Файл themes.txt не найден!")
        return
    
    print(f"Найдено {len(themes)} тем для парсинга")
    
    results = []
    base_url = "https://gu.spb.ru/knowledge-base/"
    
    for i, theme in enumerate(themes, 1):
        url = base_url + theme + '/'
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            section_tag = soup.find('section', class_='line-leading')
            
            title = "Не найдено"
            description = "Не найдено"
            
            if section_tag:
                heading_tag = section_tag.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                if heading_tag:
                    title = clean_text(heading_tag.get_text())
                
                paragraphs = section_tag.find_all('p')
                if paragraphs:
                    description_texts = []
                    for p in paragraphs:
                        text = clean_text(p.get_text())
                        if text and text != title:  
                            description_texts.append(text)
                    description = ' '.join(description_texts)
            
            main_content = "Не найдено"
            main_tag = soup.find('main', class_='line-primary line-adaptive_540-leading')
            if main_tag:
                main_copy = BeautifulSoup(str(main_tag), 'html.parser')
                
                for link in main_copy.find_all('a'):
                    link_text = clean_text(link.get_text())
                    link_url = link.get('href', '')
                    
                    if link_url.startswith('/'):
                        link_url = 'https://gu.spb.ru' + link_url
                    
                    if link_text and link_url:
                        link.replace_with(f"{link_text} ({link_url})")
                    elif link_text:
                        link.replace_with(link_text)
                
                main_text = main_copy.get_text(separator=' ')
                main_content = clean_text(main_text)
            
            results.append({
                'Название': title,
                'Описание': description,
                'Основная_часть': main_content,
                'URL': url
            })
            
            print(f"{i}/{len(themes)} Обработано: {theme}")
            
        except requests.RequestException as e:
            print(f"Ошибка загрузки {theme}: {e}")
            results.append({
                'Название': f"Ошибка: {theme}",
                'Описание': "Не удалось загрузить страницу",
                'Основная_часть': "Не удалось загрузить страницу", 
                'URL': url
            })
        except Exception as e:
            print(f"Ошибка парсинга {theme}: {e}")
            results.append({
                'Название': f"Ошибка парсинга: {theme}",
                'Описание': "Ошибка при обработке страницы",
                'Основная_часть': "Ошибка при обработке страницы", 
                'URL': url
            })
    
    save_to_text_file(results, 'all_parsed_data.txt')
    print(f"\nВсе данные сохранены в all_parsed_data.txt")
    print(f"Успешно обработано: {len([r for r in results if 'Ошибка' not in r['Название']])} из {len(themes)}")
    
    return results

results = parse_all_themes()
