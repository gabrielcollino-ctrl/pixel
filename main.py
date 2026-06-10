import discord
import os
import datetime
import asyncio
import json
from discord.ext import commands, tasks
from discord import app_commands

TOKEN = os.environ.get('TOKEN')
PIX = '31990667635'

CONFIG_FILE = 'config.json'


# ─── Config por servidor ────────────────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)

def get_guild_config(guild_id: int):
    cfg = load_config()
    return cfg.get(str(guild_id), {})

def set_guild_config(guild_id: int, data: dict):
    cfg = load_config()
    cfg[str(guild_id)] = data
    save_config(cfg)

def update_guild_config(guild_id: int, key: str, value):
    cfg = load_config()
    gid = str(guild_id)
    if gid not in cfg:
        cfg[gid] = {}
    cfg[gid][key] = value
    save_config(cfg)


# ─── Estado em memória ───────────────────────────────────────────────────────

ticket_estado = {}          # channel_id -> dict
status_messages = {}        # guild_id -> message_id
loja_status = {}            # guild_id -> bool


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_saudacao():
    hora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).hour
    if 1 <= hora <= 11:
        return '🌅 Bom dia! Tudo bem?\n\nSeja bem-vindo(a)! 😊\nSou o atendimento da Pixel Store!\n\nEscolha o tipo de servico abaixo 👇'
    elif 12 <= hora <= 17:
        return '☀️ Boa tarde! Tudo certo?\n\nSeja bem-vindo(a)! 😄\nSou o atendimento da Pixel Store!\n\nEscolha o tipo de servico abaixo 👇'
    else:
        return '🌙 Boa noite! Tudo bem?\n\nSeja bem-vindo(a)! 😊\nSou o atendimento da Pixel Store!\n\nEscolha o tipo de servico abaixo 👇'


def build_status_embed(online: bool, guild: discord.Guild):
    hora_br = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).strftime('%d/%m/%Y - %H:%M')
    if online:
        icon, text = '🟢', 'Loja Online'
        desc = 'A **Pixel Store** esta aberta e pronta para atender!'
        footer = f'Pixel Store - Online | {hora_br}'
    else:
        icon, text = '🔴', 'Loja Offline'
        desc = 'A **Pixel Store** esta temporariamente fechada.\nVolte em breve!'
        footer = f'Pixel Store - Offline | {hora_br}'

    embed = discord.Embed(title=f'{icon}  {text}', description=desc, color=0x9B59B6)
    embed.add_field(name='👥  Membros', value=f'**{guild.member_count}** membros', inline=True)
    embed.add_field(name='🛒  Servicos', value='**Build - Script - Performance**', inline=True)
    embed.set_footer(text=footer)
    return embed


def is_authorized(interaction: discord.Interaction) -> bool:
    gcfg = get_guild_config(interaction.guild_id)
    authorized_ids = gcfg.get('authorized_users', [])
    ceo_role_id = gcfg.get('ceo_role_id')
    suporte_role_id = gcfg.get('suporte_role_id')

    if interaction.user.id in authorized_ids:
        return True
    if interaction.guild:
        member = interaction.guild.get_member(interaction.user.id)
        if member:
            role_ids = [r.id for r in member.roles]
            if ceo_role_id and ceo_role_id in role_ids:
                return True
            if suporte_role_id and suporte_role_id in role_ids:
                return True
    return False


async def notificar_equipe(channel: discord.TextChannel, member: discord.Member, tipo: str):
    guild = channel.guild
    gcfg = get_guild_config(guild.id)
    mencoes = ''

    ceo_role_id = gcfg.get('ceo_role_id')
    if ceo_role_id:
        role = guild.get_role(ceo_role_id)
        if role:
            mencoes += role.mention + ' '

    suporte_role_id = gcfg.get('suporte_role_id')
    if suporte_role_id:
        role = guild.get_role(suporte_role_id)
        if role:
            mencoes += role.mention + ' '

    for uid in gcfg.get('authorized_users', []):
        u = guild.get_member(uid)
        if u:
            mencoes += u.mention + ' '

    await channel.send(f'{mencoes}novo ticket de **{member}** — Servico: **{tipo}**')


async def send_status_to_guild(guild: discord.Guild, online: bool):
    gcfg = get_guild_config(guild.id)
    loja_status[guild.id] = online
    update_guild_config(guild.id, 'loja_online', online)

    status_channel_id = gcfg.get('status_channel_id')
    channel = guild.get_channel(status_channel_id) if status_channel_id else None
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
    msg_id = status_messages.get(guild.id)
    if msg_id:
        try:
            msg = await channel.fetch_message(msg_id)
            await msg.edit(embed=embed)
            return
        except discord.NotFound:
            pass

    msg = await channel.send(embed=embed)
    status_messages[guild.id] = msg.id
    update_guild_config(guild.id, 'status_message_id', msg.id)


# ─── Views ────────────────────────────────────────────────────────────────────

class TipoServicoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _handle(self, interaction: discord.Interaction, tipo: str, titulo: str, emoji: str):
        await interaction.response.defer(ephemeral=True)
        channel_id = interaction.channel.id
        if channel_id in ticket_estado:
            ticket_estado[channel_id]['tipo'] = tipo
        embed = discord.Embed(
            title=f'{emoji}  {titulo}',
            description=f'Voce escolheu **{titulo}**!\n\nDescreva o que precisa em **uma unica mensagem** e nossa equipe vai te atender em breve! 😊',
            color=0x9B59B6
        )
        embed.set_footer(text='Pixel Store - Aguarde um momento!')
        await interaction.channel.send(embed=embed)
        await notificar_equipe(interaction.channel, interaction.user, tipo)

    @discord.ui.button(label='💬 Discord', style=discord.ButtonStyle.primary, custom_id='tipo_discord')
    async def tipo_discord(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle(interaction, 'Discord', 'Discord', '💬')

    @discord.ui.button(label='📈 Consultoria Marketing', style=discord.ButtonStyle.primary, custom_id='tipo_marketing')
    async def tipo_marketing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle(interaction, 'Consultoria Marketing', 'Consultoria de Marketing', '📈')

    @discord.ui.button(label='🎮 Build Roblox', style=discord.ButtonStyle.primary, custom_id='tipo_roblox')
    async def tipo_roblox(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle(interaction, 'Build Roblox', 'Build Roblox', '🎮')


class AbrirTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='📩 Abrir Atendimento', style=discord.ButtonStyle.primary, custom_id='abrir_ticket')
    async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        member = interaction.user
        gcfg = get_guild_config(guild.id)

        existing = discord.utils.get(guild.text_channels, name=f'ticket-{member.id}')
        if existing:
            await interaction.followup.send(f'Voce ja tem um ticket aberto! {existing.mention}', ephemeral=True)
            return

        category = discord.utils.get(guild.categories, name='tickets')
        if not category:
            category = await guild.create_category('tickets')

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        ceo_role_id = gcfg.get('ceo_role_id')
        if ceo_role_id:
            role = guild.get_role(ceo_role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        suporte_role_id = gcfg.get('suporte_role_id')
        if suporte_role_id:
            role = guild.get_role(suporte_role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        for uid in gcfg.get('authorized_users', []):
            u = guild.get_member(uid)
            if u:
                overwrites[u] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(f'ticket-{member.id}', category=category, overwrites=overwrites)
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
        await interaction.followup.send(f'Ticket aberto! {channel.mention}', ephemeral=True)


class FecharTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🔒 Fechar Ticket', style=discord.ButtonStyle.danger, custom_id='fechar_ticket')
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.channel.send('Fechando o ticket em 5 segundos...')
        await asyncio.sleep(5)
        ticket_estado.pop(interaction.channel.id, None)
        await interaction.channel.delete()


# ─── Bot ──────────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree


@tasks.loop(minutes=5)
async def atualizar_status():
    for guild in bot.guilds:
        gcfg = get_guild_config(guild.id)
        online = loja_status.get(guild.id, gcfg.get('loja_online', False))
        await send_status_to_guild(guild, online)


@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    bot.add_view(AbrirTicketView())
    bot.add_view(FecharTicketView())
    bot.add_view(TipoServicoView())

    # Carrega estado salvo de cada servidor
    cfg = load_config()
    for gid_str, gcfg in cfg.items():
        gid = int(gid_str)
        loja_status[gid] = gcfg.get('loja_online', False)
        if gcfg.get('status_message_id'):
            status_messages[gid] = gcfg['status_message_id']

    atualizar_status.start()
    try:
        synced = await tree.sync()
        print(f'{len(synced)} comandos sincronizados globalmente')
    except Exception as e:
        print(f'Erro ao sincronizar: {e}')

    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='Pixel Store'))


# ─── Comandos de configuração (apenas admins do servidor) ────────────────────

def is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.administrator


@tree.command(name='config_canal_status', description='Define o canal de status da loja')
@app_commands.describe(canal='Canal onde o status sera exibido')
async def config_canal_status(interaction: discord.Interaction, canal: discord.TextChannel):
    if not is_admin(interaction):
        await interaction.response.send_message('Apenas administradores podem configurar o bot.', ephemeral=True)
        return
    update_guild_config(interaction.guild_id, 'status_channel_id', canal.id)
    await interaction.response.send_message(f'Canal de status definido para {canal.mention}!', ephemeral=True)


@tree.command(name='config_cargo_ceo', description='Define o cargo de CEO/dono')
@app_commands.describe(cargo='Cargo com acesso total')
async def config_cargo_ceo(interaction: discord.Interaction, cargo: discord.Role):
    if not is_admin(interaction):
        await interaction.response.send_message('Apenas administradores podem configurar o bot.', ephemeral=True)
        return
    update_guild_config(interaction.guild_id, 'ceo_role_id', cargo.id)
    await interaction.response.send_message(f'Cargo CEO definido para {cargo.mention}!', ephemeral=True)


@tree.command(name='config_cargo_suporte', description='Define o cargo de suporte')
@app_commands.describe(cargo='Cargo de suporte/atendimento')
async def config_cargo_suporte(interaction: discord.Interaction, cargo: discord.Role):
    if not is_admin(interaction):
        await interaction.response.send_message('Apenas administradores podem configurar o bot.', ephemeral=True)
        return
    update_guild_config(interaction.guild_id, 'suporte_role_id', cargo.id)
    await interaction.response.send_message(f'Cargo Suporte definido para {cargo.mention}!', ephemeral=True)


@tree.command(name='config_pix', description='Define a chave PIX da loja neste servidor')
@app_commands.describe(chave='Chave PIX (telefone, CPF, email ou aleatoria)')
async def config_pix(interaction: discord.Interaction, chave: str):
    if not is_admin(interaction):
        await interaction.response.send_message('Apenas administradores podem configurar o bot.', ephemeral=True)
        return
    update_guild_config(interaction.guild_id, 'pix', chave)
    await interaction.response.send_message(f'Chave PIX definida para `{chave}`!', ephemeral=True)


@tree.command(name='config_ver', description='Mostra a configuracao atual deste servidor')
async def config_ver(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message('Apenas administradores podem ver a configuracao.', ephemeral=True)
        return
    gcfg = get_guild_config(interaction.guild_id)
    guild = interaction.guild

    status_ch = guild.get_channel(gcfg.get('status_channel_id', 0))
    ceo_role = guild.get_role(gcfg.get('ceo_role_id', 0))
    suporte_role = guild.get_role(gcfg.get('suporte_role_id', 0))
    pix = gcfg.get('pix', PIX)

    embed = discord.Embed(title='⚙️  Configuracao do Servidor', color=0x9B59B6)
    embed.add_field(name='Canal de Status', value=status_ch.mention if status_ch else '❌ Nao definido', inline=False)
    embed.add_field(name='Cargo CEO', value=ceo_role.mention if ceo_role else '❌ Nao definido', inline=True)
    embed.add_field(name='Cargo Suporte', value=suporte_role.mention if suporte_role else '❌ Nao definido', inline=True)
    embed.add_field(name='Chave PIX', value=f'`{pix}`', inline=False)
    embed.add_field(name='Loja', value='🟢 Online' if gcfg.get('loja_online') else '🔴 Offline', inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ─── Comandos da loja ────────────────────────────────────────────────────────

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
    online = loja_status.get(interaction.guild_id, False)
    embed = build_status_embed(online, interaction.guild)
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
    await interaction.channel.send(embed=embed, view=AbrirTicketView())
    await interaction.response.send_message('Painel enviado!', ephemeral=True)


@tree.command(name='aceitar', description='Aceita o pedido do cliente no ticket')
@app_commands.describe(item='O que foi pedido', preco='Valor combinado em reais (ex: 30)')
async def aceitar(interaction: discord.Interaction, item: str, preco: str):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    gcfg = get_guild_config(interaction.guild_id)
    pix = gcfg.get('pix', PIX)
    embed = discord.Embed(title='✅  Pedido Aceito!', description='Seu pedido foi **aceito** pela equipe da Pixel Store!\n\nAssim que recebermos o pagamento, iniciamos a producao! 🚀', color=0x57F287)
    embed.add_field(name='📦  Item', value=item, inline=True)
    embed.add_field(name='💰  Valor', value=f'R${preco}', inline=True)
    embed.add_field(name='🔑  Chave PIX', value=f'`{pix}`', inline=False)
    embed.add_field(name='📸  Proximo passo', value='Faca o PIX e envie o **comprovante como imagem** aqui no ticket!', inline=False)
    embed.set_footer(text='Pixel Store - Obrigado pela preferencia!')
    await interaction.response.send_message(embed=embed)


@tree.command(name='recusar', description='Recusa o pedido do cliente no ticket')
@app_commands.describe(motivo='Motivo da recusa')
async def recusar(interaction: discord.Interaction, motivo: str):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    embed = discord.Embed(title='❌  Pedido Recusado', description=f'Infelizmente nao foi possivel aceitar seu pedido no momento.\n\n**Motivo:** {motivo}\n\nSe tiver duvidas, entre em contato com nossa equipe!', color=0xED4245)
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
