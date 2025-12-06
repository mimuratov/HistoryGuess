import asyncio
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, \
    KeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from database import db

BOT_TOKEN = "7649318641:AAGEArwpLI7wX3VHswGKSYczsZWlOu5Xgcw"

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)


class QuizStates(StatesGroup):
    in_quiz = State()


def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Начать викторину")],
            [KeyboardButton(text="📖 Помощь")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )


def get_quiz_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Верю", callback_data="answer_true")],
            [InlineKeyboardButton(text="❌ Не верю", callback_data="answer_false")],
            [InlineKeyboardButton(text="🚪 Выйти", callback_data="exit_quiz")]
        ]
    )


def get_continue_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Следующий вопрос", callback_data="next_question")],
            [InlineKeyboardButton(text="🚪 Выйти", callback_data="exit_quiz")]
        ]
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "📚 *Историческая правда или миф?*\n\n"
        "Проверьте свои знания по истории России до Ивана III!\n\n"
        "🎮 *Доступные действия:*\n"
        "• Начать викторину - проверьте свои знания\n"
        "• Помощь - как пользоваться ботом\n\n"
        "ℹ️ В викторине 50 вопросов. Отвечайте 'Верю' или 'Не верю'."
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_menu())


@router.message(lambda message: message.text == "📖 Помощь")
async def cmd_help(message: Message):
    help_text = (
        "📖 *Как пользоваться ботом:*\n\n"
        "1. Нажмите '🎮 Начать викторину'\n"
        "2. Читайте утверждение и выбирайте:\n"
        "   ✅ *Верю* - если думаете, что это правда\n"
        "   ❌ *Не верю* - если думаете, что это миф\n"
        "3. После ответа получите объяснение\n"
        "4. Можете продолжить или выйти\n\n"
        "🚪 Выйти из викторины можно в любой момент"
    )
    await message.answer(help_text, parse_mode="Markdown", reply_markup=get_main_menu())


@router.message(lambda message: message.text == "🎮 Начать викторину")
async def start_quiz(message: Message, state: FSMContext):
    await db.reset_session(message.from_user.id)

    question = await db.get_next_question(message.from_user.id)

    if not question:
        await message.answer(
            "🎉 Поздравляем! Вы ответили на все вопросы!\n"
            "Нажмите '🎮 Начать викторину' чтобы начать заново.",
            reply_markup=get_main_menu()
        )
        return

    await state.set_state(QuizStates.in_quiz)

    question_text = (
        f"*Тема: {question.get('theme', 'Общая история')}*\n\n"
        f"{question['text']}\n\n"
        f"Выберите вариант ответа:"
    )

    await message.answer(question_text, parse_mode="Markdown", reply_markup=get_quiz_keyboard())


@router.callback_query(lambda c: c.data.startswith('answer_'))
async def process_answer(callback: CallbackQuery, state: FSMContext):
    user_answer = callback.data == "answer_true"
    result = await db.check_answer(callback.from_user.id, user_answer)

    answer_emoji = "✅" if result['correct'] else "❌"
    correct_text = "ПРАВДА" if result['correct_answer'] else "МИФ"

    response_text = (
        f"{answer_emoji} *{'Верно!' if result['correct'] else 'Неверно!'}*\n\n"
        f"Правильный ответ: *{correct_text}*\n\n"
        f"📝 *Объяснение:* {result['comment']}\n\n"
        f"Хотите продолжить?"
    )

    await callback.message.edit_text(response_text, parse_mode="Markdown", reply_markup=get_continue_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data == "next_question")
async def next_question(callback: CallbackQuery, state: FSMContext):
    question = await db.get_next_question(callback.from_user.id)

    if not question:
        await state.clear()
        await db.reset_session(callback.from_user.id)
        await callback.message.edit_text(
            "🎉 Поздравляем! Вы ответили на все вопросы!\n\n"
            "Нажмите '🎮 Начать викторину' чтобы начать заново.",
            reply_markup=get_main_menu()
        )
        return

    question_text = (
        f"*Тема: {question.get('theme', 'Общая история')}*\n\n"
        f"{question['text']}\n\n"
        f"Выберите вариант ответа:"
    )

    await callback.message.edit_text(question_text, parse_mode="Markdown", reply_markup=get_quiz_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data == "exit_quiz")
async def exit_quiz(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await db.reset_session(callback.from_user.id)
        await callback.message.delete()
        await callback.message.answer(
            "🚪 Вы вышли из викторины.\n\n"
            "Чтобы начать новую викторину, используйте меню ниже:",
            reply_markup=get_main_menu()
        )
    except Exception:
        await callback.message.answer(
            "🚪 Вы вышли из викторины.\n\n"
            "Чтобы начать новую викторину, используйте меню ниже:",
            reply_markup=get_main_menu()
        )
    await callback.answer()


@router.message()
async def handle_other_messages(message: Message):
    await message.answer(
        "Используйте меню ниже для взаимодействия с ботом:",
        reply_markup=get_main_menu()
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
