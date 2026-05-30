import discord
import os
import datetime
import asyncio
from discord.ext import commands
from discord.ext import tasks
from discord import app_commands

TOKEN = os.environ.get('TOKEN')
GUILD_ID = 1488676242088792074
STATUS_CHANNEL_ID = 1498482306875134053
PIX = '31990667635'

AUTHORIZED_USER_IDS = [
    1330979364438806529,
    1187052056905797637,
    1504608567125348514,
]

CEO_ROLE_ID = 1488696715627204688
SUPORTE_ROLE_ID = 1510283520126226583
TICKET_CATEGORY_NAME = 'tickets'

ticket_estado = {}
status_message_id = None
loja_online = False


def get_saudacao():
    hora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).hour
    if 1 <= hora <= 11:
        return '🌅 Bom dia! Tudo bem?\n\nSeja bem-vindo(a)! 😊\nSou o atendimento da Pixel Store!\n\nEscolha o tipo de servico abaixo 👇'
    elif 12 <= hora <= 17:
        return '☀️ Boa tarde! Tudo certo?\n\nSeja bem-vindo(a)! 😄\nSou o atendimento da Pixel Store!\n\nEscolha o tipo de servico abaixo 👇'
    else:
        return '🌙 Boa noite! Tudo bem?\n\nSeja bem-vindo(a)! 😊\nSou o atendimento da Pixel Store!\n\nEscolha o tipo de servico abaixo 👇'


def build_status_embed(online, guild):
    member_count = guild.member_count
    hora_br = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).strftime('%d/%m/%Y - %H:%M')
    if online:
        icon = '🟢'
        text = 'Loja Online'
        desc = 'A **Pixel Store** esta aberta e pronta para atender!'
        footer = 'Pixel Store - Online | ' + hora_br
    else:
        icon = '🔴'
        text = 'Loja Offline'
        desc = 'A **Pixel Store** esta temporariamente fechada.\nVolte em breve!'
        footer = 'Pixel Store - Offline | ' + hora_br
    embed = discord.Embed(title=icon + '  ' + text, description=desc, color=0x9B59B6)
    embed.add_field(name='👥  Membros', value='**' + str(member_count) + '** membros', inline=True)
    embed.add_field(name='🛒  Servicos', value='**Build - Script - Performance**', inline=True)
    embed.set_footer(text=footer)
    return embed


async def notificar_equipe(channel, member, tipo):
    guild = channel.guild
    mencoes = ''
    ceo_role = guild.get_role(CEO_ROLE_ID)
    if ceo_role:
        mencoes += ceo_role.mention + ' '
    suporte_role = guild.get_role(SUPORTE_ROLE_ID)
    if suporte_role:
        mencoes += suporte_role.mention + ' '
    for uid in AUTHORIZED_USER_IDS:
        user = guild.get_member(uid)
        if user:
            mencoes += user.mention + ' '
    await channel.send(mencoes + 'novo ticket de **' + str(member) + '** — Servico: **' + tipo + '**')


class TipoServicoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='💬 Discord', style=discord.ButtonStyle.primary, custom_id='tipo_discord')
    async def tipo_discord(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        channel_id = interaction.channel.id
        if channel_id in ticket_estado:
            ticket_estado[channel_id]['tipo'] = 'Discord'
        embed = discord.Embed(
            title='💬  Discord',
            description='Voce escolheu **Discord**!\n\nDescreva o que precisa em **uma unica mensagem** e nossa equipe vai te atender em breve! 😊',
            color=0x9B59B6
        )
        embed.set_footer(text='Pixel Store - Aguarde um momento!')
        await interaction.channel.send(embed=embed)
        await notificar_equipe(interaction.channel, interaction.user, 'Discord')

    @discord.ui.button(label='📈 Consultoria Marketing', style=discord.ButtonStyle.primary, custom_id='tipo_marketing')
    async def tipo_marketing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        channel_id = interaction.channel.id
        if channel_id in ticket_estado:
            ticket_estado[channel_id]['tipo'] = 'Consultoria Marketing'
        embed = discord.Embed(
            title='📈  Consultoria de Marketing',
            description='Voce escolheu **Consultoria de Marketing**!\n\nDescreva o que precisa em **uma unica mensagem** e nossa equipe vai te atender em breve! 😊',
            color=0x9B59B6
        )
        embed.set_footer(text='Pixel Store - Aguarde um momento!')
        await interaction.channel.send(embed=embed)
        await notificar_equipe(interaction.channel, interaction.user, 'Consultoria Marketing')

    @discord.ui.button(label='🎮 Build Roblox', style=discord.ButtonStyle.primary, custom_id='tipo_roblox')
    async def tipo_roblox(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        channel_id = interaction.channel.id
        if channel_id in ticket_estado:
            ticket_estado[channel_id]['tipo'] = 'Build Roblox'
        embed = discord.Embed(
            title='🎮  Build Roblox',
            description='Voce escolheu **Build Roblox**!\n\nDescreva o que precisa em **uma unica mensagem** e nossa equipe vai te atender em breve! 😊',
            color=0x9B59B6
        )
        embed.set_footer(text='Pixel Store - Aguarde um momento!')
        await interaction.channel.send(embed=embed)
        await notificar_equipe(interaction.channel, interaction.user, 'Build Roblox')


class AbrirTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='📩 Abrir Atendimento', style=discord.ButtonStyle.primary, custom_id='abrir_ticket')
    async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        member = interaction.user
        existing = discord.utils.get(guild.text_channels, name='ticket-' + str(member.id))
        if existing:
            await interaction.followup.send('Voce ja tem um ticket aberto! ' + existing.mention, ephemeral=True)
            return
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        ceo_role = guild.get_role(CEO_ROLE_ID)
        if ceo_role:
            overwrites[ceo_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        suporte_role = guild.get_role(SUPORTE_ROLE_ID)
        if suporte_role:
            overwrites[suporte_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        for uid in AUTHORIZED_USER_IDS:
            user = guild.get_member(uid)
            if user:
                overwrites[user] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        channel = await guild.create_text_channel('ticket-' + str(member.id), category=category, overwrites=overwrites)
        ticket_estado[channel.id] = {
            'tipo': None,
            'cliente': str(member),
            'cliente_id': member.id,
            'horario': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).strftime('%d/%m/%Y %H:%M'),
        }
        embed_bv = discord.Embed(
            title='👋  Bem-vindo(a) a Pixel Store!',
            description=get_saudacao(),
            color=0x9B59B6
        )
        embed_bv.set_footer(text='Pixel Store - Build • Script • Performance')
        await channel.send(embed=embed_bv, view=TipoServicoView())
        await channel.send(view=FecharTicketView())
        await interaction.followup.send('Ticket aberto! ' + channel.mention, ephemeral=True)


class FecharTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🔒 Fechar Ticket', style=discord.ButtonStyle.danger, custom_id='fechar_ticket')
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.channel.send('Fechando o ticket em 5 segundos...')
        await asyncio.sleep(5)
        if interaction.channel.id in ticket_estado:
            del ticket_estado[interaction.channel.id]
        await interaction.channel.delete()


intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree


@tasks.loop(minutes=5)
async def atualizar_status():
    global status_message_id, loja_online
    for guild in bot.guilds:
        channel = guild.get_channel(STATUS_CHANNEL_ID)
        if not channel:
            for ch in guild.text_channels:
                if 'status' in ch.name.lower():
                    channel = ch
                    break
        if not channel:
            continue
        embed = build_status_embed(loja_online, guild)
        if status_message_id:
            try:
                msg = await channel.fetch_message(status_message_id)
                await msg.edit(embed=embed)
                return
            except discord.NotFound:
                pass
        msg = await channel.send(embed=embed)
        status_message_id = msg.id


@bot.event
async def on_ready():
    print('Bot conectado como ' + str(bot.user))
    bot.add_view(AbrirTicketView())
    bot.add_view(FecharTicketView())
    bot.add_view(TipoServicoView())
    atualizar_status.start()
    try:
        synced = await tree.sync()
        print(str(len(synced)) + ' comandos sincronizados')
    except Exception as e:
        print('Erro: ' + str(e))
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='Pixel Store'))


def is_authorized(interaction):
    if interaction.user.id in AUTHORIZED_USER_IDS:
        return True
    if interaction.guild:
        member = interaction.guild.get_member(interaction.user.id)
        if member:
            role_ids = [r.id for r in member.roles]
            if CEO_ROLE_ID in role_ids or SUPORTE_ROLE_ID in role_ids:
                return True
    return False


async def send_status_to_guild(guild, online):
    global status_message_id, loja_online
    loja_online = online
    channel = guild.get_channel(STATUS_CHANNEL_ID)
    if not channel:
        for ch in guild.text_channels:
            if 'status' in ch.name.lower():
                channel = ch
                break
    if not channel:
        channel = guild.text_channels[0] if guild.text_channels else None
    if not channel:
        return
    embed = build_status_embed(online, guild)
    if status_message_id:
        try:
            msg = await channel.fetch_message(status_message_id)
            await msg.edit(embed=embed)
            return
        except discord.NotFound:
            pass
    msg = await channel.send(embed=embed)
    status_message_id = msg.id


@tree.command(name='lojaon', description='Coloca a Pixel Store como ONLINE')
async def lojaon(interaction: discord.Interaction):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    await send_status_to_guild(interaction.guild, True)
    await interaction.followup.send('Loja definida como ONLINE!', ephemeral=True)


@tree.command(name='lojaoff', description='Coloca a Pixel Store como OFFLINE')
async def lojaoff(interaction: discord.Interaction):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    await send_status_to_guild(interaction.guild, False)
    await interaction.followup.send('Loja definida como OFFLINE!', ephemeral=True)


@tree.command(name='status', description='Mostra o status atual da Pixel Store')
async def status_cmd(interaction: discord.Interaction):
    embed = build_status_embed(loja_online, interaction.guild)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name='atendimento', description='Envia o painel de atendimento com botao de ticket')
async def atendimento(interaction: discord.Interaction):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    embed = discord.Embed(
        title='🛒  Pixel Store - Atendimento',
        description='Clique no botao abaixo para abrir um ticket!\n\nFazemos **encomendas** de builds, scripts, mapas e muito mais para **Roblox Studio**.',
        color=0x9B59B6
    )
    embed.add_field(name='⚡  Diferenciais', value='✅ Entrega rapida\n✅ Fotos do andamento\n✅ Qualidade profissional\n✅ Precos acessiveis', inline=False)
    embed.set_footer(text='Pixel Store - Build • Script • Performance')
    await interaction.response.send_message(embed=embed, view=AbrirTicketView())


@tree.command(name='aceitar', description='Aceita o pedido do cliente no ticket')
@app_commands.describe(item='O que foi pedido', preco='Valor combinado em reais (ex: 30)')
async def aceitar(interaction: discord.Interaction, item: str, preco: str):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    embed = discord.Embed(title='✅  Pedido Aceito!', description='Seu pedido foi **aceito** pela equipe da Pixel Store!\n\nAssim que recebermos o pagamento, iniciamos a producao! 🚀', color=0x57F287)
    embed.add_field(name='📦  Item', value=item, inline=True)
    embed.add_field(name='💰  Valor', value='R$' + preco, inline=True)
    embed.add_field(name='🔑  Chave PIX', value='`' + PIX + '`', inline=False)
    embed.add_field(name='📸  Proximo passo', value='Faca o PIX e envie o **comprovante como imagem** aqui no ticket!', inline=False)
    embed.set_footer(text='Pixel Store - Obrigado pela preferencia!')
    await interaction.response.send_message(embed=embed)


@tree.command(name='recusar', description='Recusa o pedido do cliente no ticket')
@app_commands.describe(motivo='Motivo da recusa')
async def recusar(interaction: discord.Interaction, motivo: str):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    embed = discord.Embed(title='❌  Pedido Recusado', description='Infelizmente nao foi possivel aceitar seu pedido no momento.\n\n**Motivo:** ' + motivo + '\n\nSe tiver duvidas, entre em contato com nossa equipe!', color=0xED4245)
    embed.set_footer(text='Pixel Store - Agradecemos o contato!')
    await interaction.response.send_message(embed=embed)


@tree.command(name='emproducao', description='Avisa o cliente que o pedido esta em producao')
@app_commands.describe(previsao='Previsao de entrega (ex: 2 dias, 24 horas)')
async def emproducao(interaction: discord.Interaction, previsao: str):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    embed = discord.Embed(title='⚙️  Pedido em Producao!', description='Seu pedido esta sendo produzido com muito cuidado!\n\nVamos te mandar fotos do andamento em breve 📸', color=0xF1C40F)
    embed.add_field(name='⏰  Previsao de Entrega', value=previsao, inline=False)
    embed.set_footer(text='Pixel Store - Qualidade e capricho em cada detalhe!')
    await interaction.response.send_message(embed=embed)


@tree.command(name='entregue', description='Avisa o cliente que o pedido foi entregue')
async def entregue(interaction: discord.Interaction):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    embed = discord.Embed(title='📦  Pedido Entregue!', description='Seu pedido foi **entregue** com sucesso! 🎉\n\nEsperamos que tenha gostado! Se precisar de ajustes ou tiver duvidas, fale com a gente aqui no ticket.\n\n**Obrigado por escolher a Pixel Store!** 🟣', color=0x57F287)
    embed.set_footer(text='Pixel Store - Build • Script • Performance')
    await interaction.response.send_message(embed=embed)


bot.run(TOKEN)
