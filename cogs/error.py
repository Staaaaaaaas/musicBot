from discord.ext import commands


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):
            return

        helper = "Type '>help' for help"

        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"Command not found. {helper}")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"You are missing an argument. {helper}")




def setup(bot):
    bot.add_cog(CommandErrorHandler(bot))
