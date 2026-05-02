async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "<b>TCF Bot Help</b>\n"
        "I manage Transsion Core groups, bans, appeals, and more. Select a topic below:",
        parse_mode="HTML",
        reply_markup=keyboards.help_topics_kb(),
    )