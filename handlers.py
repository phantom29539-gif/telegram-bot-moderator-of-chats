import asyncio
import time
from aiogram import F, types
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ANTIFLOOD_TIME, MAX_WARNS
from database import Database
from utils import check_bad_words, roll_dice, play_slots, format_number

# Инициализация БД
db = Database()

# Словарь для отслеживания игр (чтобы игрок не спамил командами)
games_in_progress = set()


async def register_handlers(dp):
    """Регистрация всех обработчиков"""

    # ========== БАЗОВЫЕ КОМАНДЫ ==========

    @dp.message(Command('start'))
    async def cmd_start(message: Message):
        """Обработчик команды /start"""
        user = db.get_user(
            message.from_user.id,
            message.chat.id,
            message.from_user.username or "NoUsername"
        )

        await message.answer(
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            f"Я бот-администратор этого чата.\n"
            f"Я слежу за порядком и помогаю развлекаться.\n\n"
            f"📋 Список команд: /help"
        )

    @dp.message(Command('help'))
    async def cmd_help(message: Message):
        """Обработчик команды /help"""
        is_admin = db.is_admin(message.from_user.id, message.chat.id)

        text = "📋 **Доступные команды:**\n\n"
        text += "**🎮 Игры:**\n"
        text += "/dice [ставка] - бросить кости (ставка от 1)\n"
        text += "/slot [ставка] - сыграть в слоты\n"
        text += "/balance - проверить баланс\n\n"

        text += "**ℹ️ Информация:**\n"
        text += "/help - это сообщение\n"
        text += "/rules - правила чата\n\n"

        if is_admin:
            text += "**🔨 Админ-команды:**\n"
            text += "/warn [@user] [причина] - выдать предупреждение\n"
            text += "/warns [@user] - проверить варны\n"
            text += "/unwarn [@user] - снять варн\n"
            text += "/mute [@user] [минуты] - запретить писать\n"
            text += "/ban [@user] - заблокировать\n"
            text += "/unban [@user] - разблокировать\n"
            text += "/addword [слово] - добавить в черный список\n"
            text += "/delword [слово] - удалить из черного списка"

        await message.answer(text, parse_mode="Markdown")

    @dp.message(Command('rules'))
    async def cmd_rules(message: Message):
        """Правила чата"""
        await message.answer(
            "📜 **Правила чата:**\n\n"
            "1. Уважайте друг друга\n"
            "2. Не материться\n"
            "3. Не спамить\n"
            "4. За 3 предупреждения - автоматический бан\n"
            "5. Играйте и веселитесь!",
            parse_mode="Markdown"
        )

    # ========== ЭКОНОМИКА И БАЛАНС ==========

    @dp.message(Command('balance'))
    async def cmd_balance(message: Message):
        """Проверка баланса"""
        user = db.get_user(message.from_user.id, message.chat.id)
        balance = user[5]

        await message.answer(
            f"💰 **Твой баланс:** {format_number(balance)} монет",
            parse_mode="Markdown"
        )

    # ========== ИГРЫ ==========

    @dp.message(Command('dice'))
    async def cmd_dice(message: Message):
        """Игра в кости"""
        # Проверяем, не играет ли уже пользователь
        if message.from_user.id in games_in_progress:
            await message.reply("⏳ Подожди, текущая игра еще не закончена!")
            return

        # Получаем ставку из текста сообщения
        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ Укажи ставку! Пример: /dice 50")
            return

        try:
            bet = int(args[1])
        except ValueError:
            await message.reply("❌ Ставка должна быть числом!")
            return

        if bet <= 0:
            await message.reply("❌ Ставка должна быть положительной!")
            return

        # Проверяем баланс
        user = db.get_user(message.from_user.id, message.chat.id)
        balance = user[5]

        if balance < bet:
            await message.reply(f"❌ Недостаточно монет! Твой баланс: {balance}")
            return

        # Начинаем игру
        games_in_progress.add(message.from_user.id)

        # Отправляем кубик от Telegram
        dice_msg = await message.answer_dice(emoji="🎲")
        await asyncio.sleep(3)  # Ждем анимацию

        player_score = dice_msg.dice.value
        bot_score = roll_dice()

        # Определяем результат
        if player_score > bot_score:
            win_amount = bet
            db.update_balance(message.from_user.id, message.chat.id, win_amount)
            result_text = f"🎉 **Ты выиграл!** +{win_amount} монет"
        elif player_score < bot_score:
            win_amount = -bet
            db.update_balance(message.from_user.id, message.chat.id, win_amount)
            result_text = f"😢 **Ты проиграл!** -{bet} монет"
        else:
            result_text = f"🤝 **Ничья!** Ставка возвращена"

        new_balance = db.get_balance(message.from_user.id, message.chat.id)

        await message.answer(
            f"{result_text}\n"
            f"Твой бросок: {player_score} | Бот: {bot_score}\n"
            f"💰 Новый баланс: {format_number(new_balance)}"
        )

        games_in_progress.remove(message.from_user.id)

    @dp.message(Command('slot'))
    async def cmd_slot(message: Message):
        """Игра в слоты"""
        if message.from_user.id in games_in_progress:
            await message.reply("⏳ Подожди, текущая игра еще не закончена!")
            return

        # Получаем ставку из текста сообщения
        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ Укажи ставку! Пример: /slot 50")
            return

        try:
            bet = int(args[1])
        except ValueError:
            await message.reply("❌ Ставка должна быть числом!")
            return

        if bet <= 0:
            await message.reply("❌ Ставка должна быть положительной!")
            return

        user = db.get_user(message.from_user.id, message.chat.id)
        balance = user[5]

        if balance < bet:
            await message.reply(f"❌ Недостаточно монет! Твой баланс: {balance}")
            return

        games_in_progress.add(message.from_user.id)

        # Играем в слоты
        combination, multiplier = play_slots()

        # Расчет выигрыша
        if multiplier > 0:
            win_amount = bet * multiplier
            db.update_balance(message.from_user.id, message.chat.id, win_amount)
            result_text = f"🎰 **{''.join(combination)}**\n\n"
            result_text += f"🎉 **Ты выиграл!** x{multiplier}\n"
            result_text += f"+{win_amount} монет"
        else:
            win_amount = -bet
            db.update_balance(message.from_user.id, message.chat.id, win_amount)
            result_text = f"🎰 **{''.join(combination)}**\n\n"
            result_text += f"😢 **Ты проиграл!** -{bet} монет"

        new_balance = db.get_balance(message.from_user.id, message.chat.id)

        await message.answer(
            f"{result_text}\n"
            f"💰 Новый баланс: {format_number(new_balance)}"
        )

        games_in_progress.remove(message.from_user.id)

    # ========== МОДЕРАЦИЯ (АДМИН-КОМАНДЫ) ==========

    @dp.message(Command('warn'))
    async def cmd_warn(message: Message):
        """Выдать предупреждение"""
        if not db.is_admin(message.from_user.id, message.chat.id):
            await message.reply("❌ У тебя нет прав администратора!")
            return

        # Получаем аргументы
        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ Укажи пользователя! Пример: /warn @user Причина")
            return

        target_username = args[1].replace('@', '')
        reason = ' '.join(args[2:]) if len(args) > 2 else "Без причины"

        # Ищем пользователя по username
        target_user = None
        async for member in message.chat.get_members():
            if member.user.username and member.user.username.lower() == target_username.lower():
                target_user = member.user
                break

        if not target_user:
            await message.reply("❌ Пользователь не найден в этом чате!")
            return

        # Добавляем варн
        warn_count = db.add_warn(
            target_user.id,
            message.chat.id,
            message.from_user.id,
            reason
        )

        await message.reply(
            f"⚠️ Пользователь {target_user.mention_html()} получил предупреждение {warn_count}/{MAX_WARNS}\n"
            f"Причина: {reason}",
            parse_mode="HTML"
        )

        # Проверяем на автобан
        if warn_count >= MAX_WARNS:
            try:
                await message.chat.ban(target_user.id)
                db.ban_user(target_user.id, message.chat.id)
                await message.answer(
                    f"🚫 {target_user.mention_html()} забанен автоматически за {MAX_WARNS} предупреждений!",
                    parse_mode="HTML"
                )
            except Exception as e:
                await message.answer("❌ Не удалось забанить пользователя (не хватает прав?)")

    @dp.message(Command('warns'))
    async def cmd_warns(message: Message):
        """Проверить количество варнов"""
        args = message.text.split()

        if len(args) < 2:
            # Проверяем свои варны
            warns = db.get_warns(message.from_user.id, message.chat.id)
            await message.reply(f"📊 Твои предупреждения: {warns}/{MAX_WARNS}")
        else:
            # Проверяем варны другого пользователя
            if not db.is_admin(message.from_user.id, message.chat.id):
                await message.reply("❌ Только админ может проверять чужие варны!")
                return

            target_username = args[1].replace('@', '')
            target_user = None
            async for member in message.chat.get_members():
                if member.user.username and member.user.username.lower() == target_username.lower():
                    target_user = member.user
                    break

            if target_user:
                warns = db.get_warns(target_user.id, message.chat.id)
                await message.reply(f"📊 Предупреждения {target_user.mention_html()}: {warns}/{MAX_WARNS}",
                                    parse_mode="HTML")
            else:
                await message.reply("❌ Пользователь не найден!")

    @dp.message(Command('unwarn'))
    async def cmd_unwarn(message: Message):
        """Снять одно предупреждение"""
        if not db.is_admin(message.from_user.id, message.chat.id):
            await message.reply("❌ У тебя нет прав администратора!")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ Укажи пользователя!")
            return

        target_username = args[1].replace('@', '')
        target_user = None
        async for member in message.chat.get_members():
            if member.user.username and member.user.username.lower() == target_username.lower():
                target_user = member.user
                break

        if target_user:
            current_warns = db.get_warns(target_user.id, message.chat.id)
            if current_warns > 0:
                # Уменьшаем на 1 (для простоты - просто очищаем все и ставим текущие - 1)
                db.clear_warns(target_user.id, message.chat.id)
                for _ in range(current_warns - 1):
                    db.add_warn(target_user.id, message.chat.id, message.from_user.id, "Снято")

                await message.reply(f"✅ Снято одно предупреждение с {target_user.mention_html()}", parse_mode="HTML")
            else:
                await message.reply("❌ У пользователя нет предупреждений!")
        else:
            await message.reply("❌ Пользователь не найден!")

    @dp.message(Command('mute'))
    async def cmd_mute(message: Message):
        """Замутить пользователя"""
        if not db.is_admin(message.from_user.id, message.chat.id):
            await message.reply("❌ У тебя нет прав администратора!")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ Укажи пользователя и время! Пример: /mute @user 10")
            return

        target_username = args[1].replace('@', '')

        try:
            minutes = int(args[2]) if len(args) > 2 else 5
        except ValueError:
            minutes = 5

        seconds = minutes * 60

        target_user = None
        async for member in message.chat.get_members():
            if member.user.username and member.user.username.lower() == target_username.lower():
                target_user = member.user
                break

        if target_user:
            try:
                # Ограничиваем права (запрещаем отправлять сообщения)
                permissions = ChatPermissions(can_send_messages=False)
                await message.chat.restrict(target_user.id, permissions, until_date=time.time() + seconds)

                # Сохраняем в БД
                db.mute_user(target_user.id, message.chat.id, seconds)

                await message.reply(
                    f"🔇 {target_user.mention_html()} замучен на {minutes} мин.",
                    parse_mode="HTML"
                )
            except Exception as e:
                await message.reply("❌ Не удалось замутить (не хватает прав?)")
        else:
            await message.reply("❌ Пользователь не найден!")

    @dp.message(Command('ban'))
    async def cmd_ban(message: Message):
        """Забанить пользователя"""
        if not db.is_admin(message.from_user.id, message.chat.id):
            await message.reply("❌ У тебя нет прав администратора!")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ Укажи пользователя!")
            return

        target_username = args[1].replace('@', '')
        target_user = None
        async for member in message.chat.get_members():
            if member.user.username and member.user.username.lower() == target_username.lower():
                target_user = member.user
                break

        if target_user:
            try:
                await message.chat.ban(target_user.id)
                db.ban_user(target_user.id, message.chat.id)
                await message.reply(f"🚫 {target_user.mention_html()} забанен!", parse_mode="HTML")
            except Exception as e:
                await message.reply("❌ Не удалось забанить (не хватает прав?)")
        else:
            await message.reply("❌ Пользователь не найден!")

    @dp.message(Command('unban'))
    async def cmd_unban(message: Message):
        """Разбанить пользователя"""
        if not db.is_admin(message.from_user.id, message.chat.id):
            await message.reply("❌ У тебя нет прав администратора!")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ Укажи пользователя!")
            return

        target_username = args[1].replace('@', '')

        try:
            # Для разбана нужен ID, но в Telegram можно разбанить по username
            # Этот метод работает, если пользователь уже был забанен
            await message.chat.unban(target_username)
            await message.reply(f"✅ Пользователь {target_username} разбанен!")
        except Exception as e:
            await message.reply("❌ Не удалось разбанить. Возможно, пользователь не был забанен.")

    @dp.message(Command('addword'))
    async def cmd_addword(message: Message):
        """Добавить слово в черный список"""
        if not db.is_admin(message.from_user.id, message.chat.id):
            await message.reply("❌ У тебя нет прав администратора!")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ Укажи слово!")
            return

        word = ' '.join(args[1:]).strip().lower()
        db.add_banned_word(message.chat.id, word)
        await message.reply(f"✅ Слово '{word}' добавлено в черный список!")

    @dp.message(Command('delword'))
    async def cmd_delword(message: Message):
        """Удалить слово из черного списка"""
        if not db.is_admin(message.from_user.id, message.chat.id):
            await message.reply("❌ У тебя нет прав администратора!")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ Укажи слово!")
            return

        word = ' '.join(args[1:]).strip().lower()
        db.remove_banned_word(message.chat.id, word)
        await message.reply(f"✅ Слово '{word}' удалено из черного списка!")

    # ========== АВТОМАТИЧЕСКАЯ МОДЕРАЦИЯ ==========

    @dp.message()
    async def auto_moderation(message: Message):
        """Автоматическая проверка всех сообщений"""
        # Игнорируем служебные сообщения и сообщения от ботов
        if message.from_user.is_bot:
            return

        # Игнорируем команды (начинаются с /)
        if message.text and message.text.startswith('/'):
            return

        # Проверяем, не замучен ли пользователь
        if db.is_muted(message.from_user.id, message.chat.id):
            try:
                await message.delete()
            except:
                pass
            return

        # АНТИФЛУД
        current_time = int(time.time())
        last_time = db.get_last_message_time(message.from_user.id, message.chat.id)

        if current_time - last_time < ANTIFLOOD_TIME and last_time != 0:
            try:
                await message.delete()
                warn_msg = await message.answer(
                    f"⏱ {message.from_user.first_name}, не флуди! Подожди {ANTIFLOOD_TIME} секунд.",
                    delete_after=3
                )
            except:
                pass
            return

        db.update_last_message_time(message.from_user.id, message.chat.id, current_time)

        # ПРОВЕРКА ЗАПРЕЩЕННЫХ СЛОВ
        if message.text:
            banned_words = db.get_banned_words(message.chat.id)
            if check_bad_words(message.text, banned_words):
                try:
                    await message.delete()

                    # Выдаем предупреждение автоматически
                    warn_count = db.add_warn(
                        message.from_user.id,
                        message.chat.id,
                        7777777,  # ID "Системы"
                        "Использование запрещенного слова"
                    )

                    await message.answer(
                        f"⚠️ {message.from_user.first_name}, использование запрещенных слов запрещено!\n"
                        f"Предупреждение: {warn_count}/{MAX_WARNS}"
                    )

                    # Проверяем на автобан
                    if warn_count >= MAX_WARNS:
                        try:
                            await message.chat.ban(message.from_user.id)
                            db.ban_user(message.from_user.id, message.chat.id)
                            await message.answer(
                                f"🚫 {message.from_user.first_name} забанен автоматически за {MAX_WARNS} предупреждений!"
                            )
                        except:
                            pass
                except:
                    pass