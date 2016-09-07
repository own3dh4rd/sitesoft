# sitesoft

Для работы:
>> pip3 install BeautifulSoup
>> pip3 install lxml
>> pip3 install redis
installing redis: http://redis.io/topics/quickstart


Запуск:
  Загрузить данные по URL: >> python3 sitesoft.py load URL --depth N
  --depth - глубина обхода веб-сайта, N=0...2
  
  Выгрузить из БД по URL : >> python3 sitesoft.py get URL -n M
  -n - n прогруженных страниц
