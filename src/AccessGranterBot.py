import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from urllib import parse
import os
from dotenv import load_dotenv
import BlockchainInteraction

BASE_URI = 'https://gfx73.github.io/AccessGranterBot/site/'
SELLER_PAGE_URI = BASE_URI + 'seller_page.html'
CUSTOMER_PAGE_URI = BASE_URI + 'customer_page.html'


async def start(update: Update, _) -> None:
    with open("../assets/general_guide.txt", 'r') as f:
        help_text = f.read()
    await update.message.reply_text(
        help_text,
        parse_mode=telegram.constants.ParseMode.MARKDOWN_V2
    )


async def help_seller(update: Update, _) -> None:
    with open("../assets/seller_guide.txt", 'r') as f:
        help_text = f.read()
    await update.message.reply_text(
        help_text,
        parse_mode=telegram.constants.ParseMode.MARKDOWN_V2
    )


async def help_customer(update: Update, _) -> None:
    with open("../assets/customer_guide.txt", 'r') as f:
        help_text = f.read()
    await update.message.reply_text(
        help_text,
        parse_mode=telegram.constants.ParseMode.MARKDOWN_V2
    )


async def get_id(update: Update, _):
    await update.message.reply_text(f"`{str(update.message.chat_id)}`",
                                    parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)


async def check_sell_correctness(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not 1 < len(context.args) < 4:
        await update.message.reply_text("Invalid number of arguments")
        return False

    group_id, price = context.args[0:2]
    if len(context.args) == 2:
        max_accesses = 0
    else:
        max_accesses = context.args[2]

    try:
        group_id = int(group_id)
    except ValueError:
        await update.message.reply_text("group_id is non integer")
        return False

    try:
        price = float(price)
    except ValueError:
        await update.message.reply_text("eth_price is non float")
        return False

    if price < 0:
        await update.message.reply_text("eth_price should be positive")
        return False

    try:
        max_accesses = int(max_accesses)
    except ValueError:
        await update.message.reply_text("members_limit should be integer")
        return False

    if max_accesses < 0:
        await update.message.reply_text("members_limit should be non negative")
        return False

    caller = update.message.from_user.id
    member = await context.application.bot.get_chat_member(group_id, caller)
    if member.status != telegram.constants.ChatMemberStatus.OWNER:
        await update.message.reply_text("Only owner can sell")
        return False

    if BlockchainInteraction.shop_exists(group_id):
        await update.message.reply_text("A shop for this group already exists")
        return False

    return group_id, price, max_accesses


async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = await check_sell_correctness(update, context)
    if not res:
        return
    group_id, price, max_accesses = res
    sig = BlockchainInteraction.sign(group_id)
    request_access_link = (await context.application.bot.create_chat_invite_link(
        group_id,
        creates_join_request=True)).invite_link
    request_access_link = parse.quote(request_access_link)

    link = f'{SELLER_PAGE_URI}?group_id={group_id}&request_access_link={request_access_link}&sig={sig}&price={price}' \
           f'&max_accesses={max_accesses}'
    await update.message.reply_text(
        link)


async def get_shop_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("You should pass exactly one argument")
        return

    group_id = context.args[0]

    try:
        group_id = int(group_id)
    except ValueError:
        await update.message.reply_text("group_id is non integer")
        return

    if not BlockchainInteraction.shop_exists(group_id):
        await update.message.reply_text("A shop for group with such id does not exist")
        return

    shop_info = BlockchainInteraction.get_shop_info(group_id)
    shop_info['Request access link'] = f"`{shop_info['Request access link']}`"
    shop_info_md = '\n'.join(f'{k}: {v}' for k, v in shop_info.items())
    await update.message.reply_markdown_v2(shop_info_md)


async def buy_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("You should pass exactly one argument")
        return

    group_id = context.args[0]

    try:
        group_id = int(group_id)
    except ValueError:
        await update.message.reply_text("group_id is non integer")
        return

    if not BlockchainInteraction.shop_exists(group_id):
        await update.message.reply_text("A shop for group with such id does not exist")
        return

    if not BlockchainInteraction.has_available_place(group_id):
        await update.message.reply_text("This shop does not have any free slots")
        return

    contract_address = BlockchainInteraction.get_shop_address(group_id)
    caller = update.message.from_user.id
    if BlockchainInteraction.did_user_buy(group_id, caller):
        await update.message.reply_text("You already bought access to this group")
        return

    link = f'{CUSTOMER_PAGE_URI}?contract_address={contract_address}&user_id={caller}'
    await update.message.reply_text(link)


async def get_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("You should pass exactly one argument")
        return

    group_id = context.args[0]

    try:
        group_id = int(group_id)
    except ValueError:
        await update.message.reply_text("group_id is non integer")
        return

    if not BlockchainInteraction.shop_exists(group_id):
        await update.message.reply_text("A shop for group with such id does not exist")
        return

    caller = update.message.from_user.id
    if not BlockchainInteraction.did_user_buy(group_id, caller):
        await update.message.reply_text("You did not buy an access to this group")
        return

    try:
        result: bool = await context.application.bot.approve_chat_join_request(group_id, caller)
        if not result:
            await update.message.reply_text("Failure. Make sure you requested the join." +
                                            " Maybe you are already a member of the group.")
            return
    except:
        await update.message.reply_text("Failure. Make sure you requested the join." +
                                        " Maybe you are already a member of the group.")
        return

    await update.message.reply_text("Your join request is approved. " +
                                    "If you did not request the join, do it and rerun the command")


def main():
    load_dotenv()
    api_key = os.getenv('API_KEY')
    application = Application.builder().token(api_key).build()

    application.add_handler(CommandHandler(["start", "help"], start))
    application.add_handler(CommandHandler("help_seller", help_seller))
    application.add_handler(CommandHandler("help_customer", help_customer))
    application.add_handler(CommandHandler("get_id", get_id))
    application.add_handler(CommandHandler("sell", sell))
    application.add_handler(CommandHandler('get_shop_info', get_shop_info))
    application.add_handler(CommandHandler('buy_access', buy_access))
    application.add_handler(CommandHandler('get_access', get_access))

    application.run_polling()


if __name__ == '__main__':
    print('bot started')
    main()
