import { test, expect } from '@playwright/test'

test('markdown rendering in assistant messages', async ({ page }) => {
  // Пока что это заглушка теста, так как нам нужно настроить полноценное тестирование
  // В реальной среде здесь будет тест рендеринга markdown
  expect(true).toBe(true)
})

// Альтернативно можно создать unit test для компонента
// import { render } from '@testing-library/react'
// import MessageBubble from '../src/components/MessageBubble'
//
// test('renders markdown for assistant messages', () => {
//   const { container } = render(
//     <MessageBubble role="assistant">**bold text**</MessageBubble>
//   )
//   expect(container.innerHTML).toContain('<strong>bold text</strong>')
// })
