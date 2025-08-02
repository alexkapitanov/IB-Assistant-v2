# Конфигурация Grafana для IB-Assistant

## Метод 1: Анонимный доступ (Текущая конфигурация)

### Конфигурация в `grafana/provisioning/custom/grafana.ini`:

```ini
[auth.anonymous]
enabled = true
org_role = Viewer
org_name = Main Org.
```

### Docker Compose:
```yaml
grafana:
  image: grafana/grafana:latest
  volumes:
    - ./grafana/provisioning/custom/grafana.ini:/etc/grafana/grafana.ini
```

### Frontend URL:
```typescript
const src = import.meta.env.VITE_GRAFANA_URL +
            "/d/ib-overview/ib-assistant-overview?refresh=30s&kiosk=tv";
```

## Метод 2: API Key (Альтернативный подход)

### 1. Создание API ключа

Войти в Grafana как админ (admin/admin) и создать API ключ:
- Зайти в Configuration → API Keys
- Нажать "New API Key"
- Name: `viewer-key`
- Role: `Viewer`
- Time to live: `1y` (или другое значение)

### 2. Использование в frontend

```bash
# В .env файле
VITE_GRAFANA_URL=http://localhost:3000
VITE_GRAFANA_API_KEY=eyJrIjoi...  # Ваш API ключ
```

```typescript
// В компоненте GrafanaEmbed.tsx
export default function GrafanaEmbed() {
  const apiKey = import.meta.env.VITE_GRAFANA_API_KEY;
  const src = import.meta.env.VITE_GRAFANA_URL +
              `/d/ib-overview/ib-assistant-overview?refresh=30s&kiosk=tv${apiKey ? `&auth_token=${apiKey}` : ''}`;
  
  return (
    <iframe 
      src={src}
      className="w-full h-screen border-0"
      title="IB Grafana Dashboard"
      loading="lazy"
    />
  );
}
```

### 3. Curl команда для создания API ключа

```bash
# Создание API ключа через curl
curl -X POST "http://localhost:3000/api/auth/keys" \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic $(echo -n 'admin:admin' | base64)" \
  -d '{
    "name": "viewer-key",
    "role": "Viewer",
    "secondsToLive": 31536000
  }'
```

## Преимущества каждого подхода

### Анонимный доступ:
- ✅ Простота настройки
- ✅ Не нужно управлять ключами
- ✅ Работает сразу после развертывания
- ❌ Менее безопасно для продакшена

### API Key:
- ✅ Более безопасно
- ✅ Можно отозвать ключ
- ✅ Контроль доступа
- ❌ Требует дополнительной настройки
- ❌ Нужно обновлять ключи при истечении

## Рекомендации

- Для **development/testing**: используйте анонимный доступ
- Для **production**: используйте API ключи с ограниченными правами
- Всегда используйте HTTPS в продакшене
- Регулярно обновляйте API ключи
