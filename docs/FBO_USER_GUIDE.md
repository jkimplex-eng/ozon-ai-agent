# FBO: инструкция для пользователя

## Что делает модуль

Модуль FBO отвечает на три простых вопроса:
1. Какой спрос ожидается по каждому SKU на 30, 60 и 90 дней.
2. В какой кластер нужно везти товар.
3. Сколько товара нужно дослать на FBO уже сейчас.

Результат автоматически:
- показывается в Telegram;
- записывается в Google Sheets.

Важно:
- расчёт выполняется автоматически;
- реальные действия по поставке защищены;
- система не создаёт поставку молча и без подтверждения.

## Где находится таблица

Рабочий лист называется:

```text
FBO Demand
```

Рабочая таблица:

```text
https://docs.google.com/spreadsheets/d/1MoakuEmSMkEEKf1TtoNkEF6wVyx_NBgheb3v-M4LqeI
```

## Самый простой путь в Telegram

Если не хочется копировать длинные ID, используйте короткий сценарий:

```text
/supply fbo
/supply fbo-propose
/supply latest-approve
/supply latest-create-draft
/supply latest-timeslots
/supply latest-book-first
```

Что это значит:
- `latest-approve` — подтвердить последнее новое предложение;
- `latest-create-draft` — создать draft по последнему подтверждённому предложению;
- `latest-timeslots` — показать слоты по последнему draft;
- `latest-book-first` — забронировать первый доступный слот.

## Полный путь в Telegram

Если нужен полный контроль по ID:

```text
/supply fbo
/supply fbo-propose
/supply proposals
/supply approve <proposal_id>
/supply create-draft <proposal_id>
/supply timeslots <draft_id>
/supply select-timeslot <proposal_id> <timeslot_id>
```

## Что смотреть в Telegram

Основные команды:

```text
/supply fbo
/supply proposals
/supply latest
/supply orders
```

`/supply latest` показывает последнее предложение, его статус, draft ID и supply ID.

## Как использовать каждый день

Рекомендуемый порядок работы:
1. Открыть Telegram и выполнить `/supply fbo`.
2. Открыть лист `FBO Demand` в Google Sheets.
3. Отсортировать строки по `Recommended 30` или `Stock Days`.
4. Посмотреть сначала самые критичные SKU.
5. Если поставка нужна, выполнить `/supply fbo-propose`.
6. Для простого пути выполнить `/supply latest-approve`.
7. Затем выполнить `/supply latest-create-draft`.
8. Проверить слоты командой `/supply latest-timeslots`.
9. Забронировать первый слот командой `/supply latest-book-first`.

## Что система делает сама

Система делает сама:
- считает спрос;
- считает рекомендуемую поставку;
- записывает расчёт в Google Sheets;
- показывает результат в Telegram;
- создаёт предложения;
- создаёт draft;
- создаёт реальную заявку Ozon;
- бронирует слот.

## Что уже работает на 30 июня 2026

Работает:
- FBO расчёт 30 / 60 / 90 дней;
- запись в Google Sheets;
- просмотр в Telegram;
- создание FBO proposals;
- подтверждение proposals;
- создание draft в Ozon;
- создание supply order в Ozon;
- бронирование timeslot.

## Следующий шаг: 1С

Самый безопасный путь интеграции с 1С такой:
1. Выгружать строки FBO в стабильную таблицу или JSON.
2. Передавать в 1С SKU, кластер, рекомендуемое количество и статус.
3. Получать обратно из 1С подтверждённое количество и номер документа.
4. Оставить бронирование слота внутри этого агента, пока интеграция 1С не будет проверена на практике.
