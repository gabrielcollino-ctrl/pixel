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
CARDAPIO_CHANNEL_ID = 1488683547547009155
PIX = '31990667635'

AUTHORIZED_USER_IDS = [
    1330979364438806529,
    1187052056905797637,
]

TICKET_CATEGORY_NAME = 'tickets'

MENU_PRINCIPAL = {
    '1': 'Casas',
    '2': 'Sedes',
    '3': 'Estadios',
    '4': 'Mapas',
    '5': 'Cidades Completas',
    '6': 'Scripts/Sistemas',
    '7': 'Veiculos',
    '8': 'NPCs',
    '9': 'HUDs/Interface',
    '10': 'Logos/GFX',
    '11': 'Discord Server',
    '12': 'Pacotes',
    '13': 'Outro',
}

SUBMENUS = {
    'Casas': {
        '1': ('Casa Favela', 8),
        '2': ('Casa Normal', 10),
        '3': ('Casa Mansao', 18),
        '4': ('Predio', 15),
    },
    'Sedes': {
        '1': ('Sede de Torcida', 30),
        '2': ('Sede Choque', 35),
        '3': ('Sede PM', 30),
        '4': ('Sede ROTA', 35),
        '5': ('Sede BOPE', 40),
        '6': ('Sede COE', 40),
        '7': ('Sede Bombeiro', 30),
        '8': ('Sede SAMU', 28),
        '9': ('Sede Exercito', 40),
        '10': ('Sede Marinha', 40),
        '11': ('Sede Aeronautica', 40),
        '12': ('Sede Trafico/Mafia', 35),
        '13': ('Sede Empresa', 25),
    },
    'Estadios': {
        '1': ('Estadio de Time (ex: Flamengo, Corinthians)', 50),
        '2': ('Estadio de Inspiracao (original)', 35),
    },
    'Mapas': {
        '1': ('Mapa Pequeno', 70),
        '2': ('Mapa Medio', 90),
        '3': ('Mapa Grande', 120),
    },
    'Cidades Completas': {
        '1': ('Cidade Pequena', 80),
        '2': ('Cidade Grande', 150),
    },
    'Scripts/Sistemas': {
        '1': ('Script Simples', 10),
        '2': ('Script Medio', 18),
        '3': ('Script Completo', 26),
    },
    'Veiculos': {
        '1': ('Veiculo Simples', 5),
        '2': ('Veiculo Detalhado', 10),
    },
    'NPCs': {
        '1': ('NPC Sem Script', 5),
        '2': ('NPC Com Script', 15),
    },
    'HUDs/Interface': {
        '1': ('Interface Simples', 10),
        '2': ('Interface Completa', 30),
    },
    'Logos/GFX': {
        '1': ('Logo Simples', 8),
        '2': ('Logo Profissional', 20),
    },
    'Discord Server': {
        '1': ('Setup Basico', 15),
        '2': ('Setup Completo', 40),
    },
    'Pacotes': {
        '1': ('Pacote Basico (Casa Normal + Mapa Peq + Script Simples + Veiculo + NPC + Interface + Logo)', 108),
        '2': ('Pacote Premium (Casa Mansao + Mapa Grande + Script Completo + Veiculo Det + NPC + Interface + Logo)', 219),
        '3': ('Pacote Servidor (Discord Completo + Mapa Grande + Scripts + Logo Prof)', 186),
    },
    'Outro': {
        '1': ('Outro - Descreva seu pedido personalizado', 0),
    },
}

ticket_estado = {}
status_message_id = None
loja_online = False
pedidos_do_dia = []
cupons_ativos = {}
promocoes_ativas = {}


def get_saudacao():
    hora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).hour
    if 1 <= hora <= 11:
        return '🌅 Bom dia! Tudo bem?\n\nSeja bem-vindo(a)! 😊\nSou o auto-atendimento da BG Store!\n\nEscolha uma categoria abaixo 👇'
    elif 12 <= hora <= 17:
        return '☀️ Boa tarde! Tudo certo?\n\nSeja bem-vindo(a)! 😄\nSou o auto-atendimento da BG Store!\n\nEscolha uma categoria abaixo 👇'
    else:
        return '🌙 Boa noite! Tudo bem?\n\nSeja bem-vindo(a)! 😊\nSou o auto-atendimento da BG Store!\n\nEscolha uma categoria abaixo 👇'


def formatar_menu_principal():
    txt = ''
    for k, v in MENU_PRINCIPAL.items():
        txt += k + ' - ' + v + '\n'
    return txt


def formatar_submenu(categoria):
    sub = SUBMENUS[categoria]
    txt = ''
    for k, (nome, preco) in sub.items():
        if preco == 0:
            txt += k + ' - ' + nome + ' - A combinar\n'
        else:
            txt += k + ' - ' + nome + ' - R$' + str(preco) + '\n'
    return txt


def formatar_carrinho(carrinho):
    if not carrinho:
        return 'Carrinho vazio'
    txt = ''
    total = 0
    for item in carrinho:
        subtotal = item['preco'] * item['qtd']
        if item['preco'] == 0:
            txt += '- ' + str(item['qtd']) + 'x ' + item['nome'] + ' = A combinar\n'
        else:
            txt += '- ' + str(item['qtd']) + 'x ' + item['nome'] + ' = R$' + str(subtotal) + '\n'
            total += subtotal
    txt += '\n💰 Total: R$' + str(total)
    if any(item['preco'] == 0 for item in carrinho):
        txt += ' + itens a combinar'
    return txt


def formatar_carrinho_com_desconto(carrinho, desconto_pct, categoria_cupom):
    if not carrinho:
        return 'Carrinho vazio', 0, 0
    txt = ''
    total = 0
    total_desconto = 0
    for item in carrinho:
        subtotal = item['preco'] * item['qtd']
        total += subtotal
        cat_item = item.get('categoria', '')
        if categoria_cupom == 'tudo' or categoria_cupom == cat_item:
            desc = int(subtotal * desconto_pct / 100)
            total_desconto += desc
            txt += '- ' + str(item['qtd']) + 'x ' + item['nome'] + ' = R$' + str(subtotal) + ' (-R$' + str(desc) + ')\n'
        else:
            txt += '- ' + str(item['qtd']) + 'x ' + item['nome'] + ' = R$' + str(subtotal) + '\n'
    final = total - total_desconto
    txt += '\n💰 Total original: R$' + str(total)
    txt += '\n🎁 Desconto: -R$' + str(total_desconto)
    txt += '\n✅ Total final: R$' + str(final)
    return txt, total, final


def calcular_total(carrinho):
    return sum(item['preco'] * item['qtd'] for item in carrinho)


def build_cardapio_embed():
    embed = discord.Embed(
        title='🛒  BG Store — Tabela de Precos',
        description='Fazemos **encomendas** personalizadas para Roblox Studio!\n✅ Entrega rapida  •  ✅ Fotos do andamento  •  ✅ Qualidade profissional',
        color=0x9B59B6
    )
    embed.add_field(name='🏠  Casas', value='> Casa Favela — R$8\n> Casa Normal — R$10\n> Casa Mansao — R$18\n> Predio — R$15', inline=True)
    embed.add_field(name='🏢  Sedes', value='> Torcida — R$30\n> Choque — R$35\n> PM — R$30\n> ROTA — R$35\n> BOPE/COE — R$40\n> Bombeiro — R$30\n> SAMU — R$28\n> Exercito/Marinha/Aero — R$40\n> Trafico/Mafia — R$35\n> Empresa — R$25', inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=False)
    embed.add_field(name='🏟️  Estadios', value='> Time (Flamengo, etc) — R$50\n> Inspiracao original — R$35', inline=True)
    embed.add_field(name='🗺️  Mapas', value='> Mapa Pequeno — R$70\n> Mapa Medio — R$90\n> Mapa Grande — R$120', inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=False)
    embed.add_field(name='🌆  Cidades Completas', value='> Cidade Pequena — R$80\n> Cidade Grande — R$150', inline=True)
    embed.add_field(name='⚙️  Scripts/Sistemas', value='> Script Simples — R$10\n> Script Medio — R$18\n> Script Completo — R$26', inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=False)
    embed.add_field(name='🚗  Veiculos', value='> Veiculo Simples — R$5\n> Veiculo Detalhado — R$10', inline=True)
    embed.add_field(name='🧍  NPCs', value='> NPC Sem Script — R$5\n> NPC Com Script — R$15', inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=False)
    embed.add_field(name='🎮  HUDs/Interface', value='> Interface Simples — R$10\n> Interface Completa — R$30', inline=True)
    embed.add_field(name='🎨  Logos/GFX', value='> Logo Simples — R$8\n> Logo Profissional — R$20', inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=False)
    embed.add_field(name='💬  Discord Server', value='> Setup Basico — R$15\n> Setup Completo — R$40', inline=True)
    embed.add_field(name='💼  Pacotes', value='> Pacote Basico — R$108\n> Pacote Premium — R$219\n> Pacote Servidor — R$186', inline=True)
    embed.add_field(name='\u200b', value='\u200b', inline=False)
    embed.add_field(name='📩  Como pedir?', value='Abra um ticket no canal de atendimento!\nApos o pagamento, iniciamos sua producao imediatamente.', inline=False)
    embed.set_footer(text='BG Store • Build • Script • Performance')
    return embed


def build_status_embed(online, guild):
    member_count = guild.member_count
    hora_br = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).strftime('%d/%m/%Y - %H:%M')
    if online:
        color = 0x57F287
        icon = '🟢'
        text = 'Loja Online'
        desc = 'A **BG Store** esta aberta e pronta para atender!'
        footer = 'BG Store - Online | ' + hora_br
    else:
        color = 0xED4245
        icon = '🔴'
        text = 'Loja Offline'
        desc = 'A **BG Store** esta temporariamente fechada.\nVolte em breve!'
        footer = 'BG Store - Offline | ' + hora_br
    embed = discord.Embed(title=icon + '  ' + text, description=desc, color=color)
    embed.add_field(name='👥  Membros', value='**' + str(member_count) + '** membros', inline=True)
    embed.add_field(name='🛒  Servicos', value='**Build - Script - Performance**', inline=True)
    embed.set_footer(text=footer)
    return embed


async def chamar_humano(interaction: discord.Interaction):
    channel_id = interaction.channel.id
    if channel_id not in ticket_estado:
        ticket_estado[channel_id] = {'etapa': 'humano'}
    ticket_estado[channel_id]['etapa'] = 'humano'
    gab = interaction.guild.get_member(1330979364438806529)
    bryan = interaction.guild.get_member(1187052056905797637)
    mencoes = ''
    if gab:
        mencoes += gab.mention + ' '
    if bryan:
        mencoes += bryan.mention
    embed = discord.Embed(
        title='👤  Atendimento Humano',
        description='Um membro da equipe vai te atender em breve!\n\nFique no ticket, estamos chegando! 😊',
        color=0xF1C40F
    )
    embed.set_footer(text='BG Store - Aguarde um momento!')
    await interaction.response.edit_message(view=None)
    await interaction.followup.send(embed=embed)
    await interaction.channel.send(mencoes + ' o cliente ' + interaction.user.mention + ' quer falar com um humano!')


class NavegacaoView(discord.ui.View):
    def __init__(self, mostrar_voltar=True):
        super().__init__(timeout=None)
        if not mostrar_voltar:
            for item in self.children:
                if hasattr(item, 'custom_id') and item.custom_id == 'voltar_atras':
                    self.remove_item(item)
                    break

    @discord.ui.button(label='⬅️ Voltar', style=discord.ButtonStyle.secondary, custom_id='voltar_atras')
    async def voltar_atras(self, interaction: discord.Interaction, button: discord.ui.Button):
        estado = ticket_estado[interaction.channel.id]
        etapa = estado['etapa']
        if etapa == 'submenu':
            estado['etapa'] = 'menu'
            estado['sub'] = None
            embed = discord.Embed(title='📋  Menu Principal', description='```' + formatar_menu_principal() + '```\nDigite o numero da categoria!', color=0x9B59B6)
            await interaction.response.send_message(embed=embed, view=NavegacaoView(mostrar_voltar=False))
        elif etapa == 'quantidade':
            estado['etapa'] = 'submenu'
            categoria = estado['sub']
            embed = discord.Embed(title='📋  ' + categoria, description='```' + formatar_submenu(categoria) + '```\nDigite o numero do item!', color=0x9B59B6)
            await interaction.response.send_message(embed=embed, view=NavegacaoView())
        else:
            estado['etapa'] = 'menu'
            estado['sub'] = None
            embed = discord.Embed(title='📋  Menu Principal', description='```' + formatar_menu_principal() + '```\nDigite o numero da categoria!', color=0x9B59B6)
            await interaction.response.send_message(embed=embed, view=NavegacaoView(mostrar_voltar=False))

    @discord.ui.button(label='🏠 Inicio', style=discord.ButtonStyle.primary, custom_id='voltar_inicio')
    async def voltar_inicio(self, interaction: discord.Interaction, button: discord.ui.Button):
        estado = ticket_estado[interaction.channel.id]
        estado['etapa'] = 'menu'
        estado['sub'] = None
        estado['item_atual'] = None
        embed = discord.Embed(title='🛒  BG Store - Auto Atendimento', description=get_saudacao(), color=0x9B59B6)
        embed.add_field(name='📋  Menu Principal', value='```' + formatar_menu_principal() + '```', inline=False)
        embed.set_footer(text='Digite o numero da categoria desejada!')
        await interaction.response.send_message(embed=embed, view=NavegacaoView(mostrar_voltar=False))

    @discord.ui.button(label='👤 Falar com humano', style=discord.ButtonStyle.danger, custom_id='humano_nav')
    async def humano(self, interaction: discord.Interaction, button: discord.ui.Button):
        await chamar_humano(interaction)


class CarrinhoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='➕ Adicionar mais', style=discord.ButtonStyle.primary, custom_id='add_mais')
    async def add_mais(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_estado[interaction.channel.id]['etapa'] = 'menu'
        ticket_estado[interaction.channel.id]['sub'] = None
        embed = discord.Embed(title='📋  Menu Principal', description='```' + formatar_menu_principal() + '```\nDigite o numero da categoria!', color=0x9B59B6)
        await interaction.response.send_message(embed=embed, view=NavegacaoView(mostrar_voltar=False))

    @discord.ui.button(label='🎁 Tenho um cupom', style=discord.ButtonStyle.secondary, custom_id='usar_cupom')
    async def usar_cupom(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_estado[interaction.channel.id]['etapa'] = 'cupom'
        await interaction.response.send_message('🎁 Digite seu **codigo de cupom**!')

    @discord.ui.button(label='✅ Finalizar pedido', style=discord.ButtonStyle.success, custom_id='finalizar')
    async def finalizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_estado[interaction.channel.id]['etapa'] = 'descricao'
        await interaction.response.send_message('📝 Descreva seu pedido com detalhes em **uma unica mensagem**!\n\nConta tudo: cores, estilo, referencias, etc 😊', view=NavegacaoView())

    @discord.ui.button(label='🗑️ Limpar carrinho', style=discord.ButtonStyle.danger, custom_id='limpar')
    async def limpar(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_estado[interaction.channel.id]['carrinho'] = []
        ticket_estado[interaction.channel.id]['etapa'] = 'menu'
        embed = discord.Embed(title='🗑️  Carrinho Limpo!', description='```' + formatar_menu_principal() + '```\nEscolha novamente!', color=0xED4245)
        await interaction.response.send_message(embed=embed, view=NavegacaoView(mostrar_voltar=False))

    @discord.ui.button(label='👤 Falar com humano', style=discord.ButtonStyle.secondary, custom_id='humano_carrinho')
    async def humano(self, interaction: discord.Interaction, button: discord.ui.Button):
        await chamar_humano(interaction)


class ConfirmarPedidoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='✅ Confirmar e Pagar', style=discord.ButtonStyle.success, custom_id='confirmar_pagar')
    async def confirmar_pagar(self, interaction: discord.Interaction, button: discord.ui.Button):
        estado = ticket_estado[interaction.channel.id]
        estado['etapa'] = 'aguardando_comprovante'
        total = estado.get('total_final') or calcular_total(estado['carrinho'])
        valor_txt = 'R$' + str(total) if total > 0 else 'A combinar com a equipe'
        embed = discord.Embed(title='💳  Dados para Pagamento', description='Faca o PIX e envie o **comprovante** aqui no chat!\n\nApos confirmarmos, iniciaremos sua encomenda! 🚀', color=0x57F287)
        embed.add_field(name='🔑  Chave PIX', value='`' + PIX + '`', inline=False)
        embed.add_field(name='💰  Valor Total', value=valor_txt, inline=False)
        if estado.get('cupom_usado'):
            embed.add_field(name='🎁  Cupom Aplicado', value=estado['cupom_usado'], inline=False)
        embed.set_footer(text='Envie o comprovante como imagem!')
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label='✏️ Reescrever descricao', style=discord.ButtonStyle.secondary, custom_id='reescrever')
    async def reescrever(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_estado[interaction.channel.id]['etapa'] = 'descricao'
        await interaction.response.send_message('📝 Descreva novamente seu pedido com detalhes em **uma unica mensagem**!', view=NavegacaoView())

    @discord.ui.button(label='🔢 Mudar itens', style=discord.ButtonStyle.danger, custom_id='mudar_itens')
    async def mudar_itens(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_estado[interaction.channel.id]['carrinho'] = []
        ticket_estado[interaction.channel.id]['etapa'] = 'menu'
        ticket_estado[interaction.channel.id]['sub'] = None
        embed = discord.Embed(title='📋  Menu Principal', description='```' + formatar_menu_principal() + '```\nDigite o numero da categoria!', color=0x9B59B6)
        await interaction.response.send_message(embed=embed, view=NavegacaoView(mostrar_voltar=False))

    @discord.ui.button(label='🏠 Voltar ao inicio', style=discord.ButtonStyle.secondary, custom_id='inicio_confirmacao')
    async def inicio(self, interaction: discord.Interaction, button: discord.ui.Button):
        estado = ticket_estado[interaction.channel.id]
        estado['etapa'] = 'menu'
        estado['sub'] = None
        estado['carrinho'] = []
        embed = discord.Embed(title='🛒  BG Store - Auto Atendimento', description=get_saudacao(), color=0x9B59B6)
        embed.add_field(name='📋  Menu Principal', value='```' + formatar_menu_principal() + '```', inline=False)
        await interaction.response.send_message(embed=embed, view=NavegacaoView(mostrar_voltar=False))


class AbrirTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='📩 Abrir Atendimento', style=discord.ButtonStyle.primary, custom_id='abrir_ticket')
    async def abrir_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        existing = discord.utils.get(guild.text_channels, name='ticket-' + str(member.id))
        if existing:
            await interaction.response.send_message('Voce ja tem um ticket aberto! ' + existing.mention, ephemeral=True)
            return
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for uid in AUTHORIZED_USER_IDS:
            user = guild.get_member(uid)
            if user:
                overwrites[user] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        channel = await guild.create_text_channel('ticket-' + str(member.id), category=category, overwrites=overwrites)
        ticket_estado[channel.id] = {'etapa': 'menu', 'sub': None, 'carrinho': [], 'descricao': '', 'item_atual': None, 'cliente': str(member), 'cliente_id': member.id, 'horario': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).strftime('%d/%m/%Y %H:%M'), 'cupom_usado': None, 'total_final': 0}
        embed = discord.Embed(title='🛒  BG Store - Auto Atendimento', description=get_saudacao(), color=0x9B59B6)
        embed.add_field(name='📋  Menu Principal', value='```' + formatar_menu_principal() + '```', inline=False)
        embed.set_footer(text='Digite o numero da categoria desejada!')
        await channel.send(embed=embed, view=FecharTicketView())
        await interaction.response.send_message('Ticket aberto! ' + channel.mention, ephemeral=True)


class FecharTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🔒 Fechar Ticket', style=discord.ButtonStyle.danger, custom_id='fechar_ticket')
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('Fechando o ticket em 5 segundos...')
        await asyncio.sleep(5)
        if interaction.channel.id in ticket_estado:
            del ticket_estado[interaction.channel.id]
        await interaction.channel.delete()


intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree


@tasks.loop(minutes=1)
async def atualizar_status():
    global status_message_id, loja_online
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    channel = guild.get_channel(STATUS_CHANNEL_ID)
    if not channel:
        return
    embed = build_status_embed(loja_online, guild)
    if status_message_id:
        try:
            msg = await channel.fetch_message(status_message_id)
            await msg.edit(embed=embed)
        except discord.NotFound:
            msg = await channel.send(embed=embed)
            status_message_id = msg.id


@tasks.loop(minutes=1)
async def verificar_promocoes():
    agora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    expiradas = [k for k, v in promocoes_ativas.items() if v['expira'] < agora]
    for k in expiradas:
        del promocoes_ativas[k]
    expirados_cupons = [k for k, v in cupons_ativos.items() if v['expira'] < agora]
    for k in expirados_cupons:
        del cupons_ativos[k]


@bot.event
async def on_ready():
    print('Bot conectado como ' + str(bot.user))
    bot.add_view(AbrirTicketView())
    bot.add_view(FecharTicketView())
    bot.add_view(CarrinhoView())
    bot.add_view(ConfirmarPedidoView())
    bot.add_view(NavegacaoView())
    bot.add_view(NavegacaoView(mostrar_voltar=False))
    atualizar_status.start()
    verificar_promocoes.start()
    try:
        synced = await tree.sync()
        print(str(len(synced)) + ' comandos sincronizados')
    except Exception as e:
        print('Erro: ' + str(e))
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='BG Store'))


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.name.startswith('ticket-'):
        channel_id = message.channel.id
        if channel_id not in ticket_estado:
            ticket_estado[channel_id] = {'etapa': 'menu', 'sub': None, 'carrinho': [], 'descricao': '', 'item_atual': None, 'cliente': str(message.author), 'cliente_id': message.author.id, 'horario': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).strftime('%d/%m/%Y %H:%M'), 'cupom_usado': None, 'total_final': 0}
        estado = ticket_estado[channel_id]
        etapa = estado['etapa']

        if etapa == 'humano':
            return

        content = message.content.strip()

        if etapa == 'menu':
            if content in MENU_PRINCIPAL:
                categoria = MENU_PRINCIPAL[content]
                estado['sub'] = categoria
                if categoria == 'Outro':
                    estado['etapa'] = 'descricao_outro'
                    await message.channel.send('📝 Descreva o que voce precisa com o maximo de detalhes em **uma unica mensagem**!\n\nNossa equipe vai analisar e passar o valor! 😊', view=NavegacaoView())
                else:
                    estado['etapa'] = 'submenu'
                    embed = discord.Embed(title='📋  ' + categoria, description='```' + formatar_submenu(categoria) + '```\nDigite o numero do item!', color=0x9B59B6)
                    await message.channel.send(embed=embed, view=NavegacaoView())
            else:
                await message.channel.send('Digite um numero de **1 a 13** para escolher a categoria! 😊', view=NavegacaoView(mostrar_voltar=False))

        elif etapa == 'submenu':
            categoria = estado['sub']
            sub = SUBMENUS[categoria]
            if content in sub:
                nome, preco = sub[content]
                estado['item_atual'] = {'nome': nome, 'preco': preco, 'categoria': categoria}
                estado['etapa'] = 'quantidade'
                await message.channel.send('Quantas unidades de **' + nome + '** voce quer? Digite o numero! 🔢', view=NavegacaoView())
            else:
                await message.channel.send('Digite um numero valido do submenu! 😊', view=NavegacaoView())

        elif etapa == 'quantidade':
            if content.isdigit() and int(content) > 0:
                qtd = int(content)
                item = estado['item_atual'].copy()
                item['qtd'] = qtd
                estado['carrinho'].append(item)
                estado['item_atual'] = None
                estado['etapa'] = 'carrinho'
                embed = discord.Embed(title='🛒  Carrinho Atualizado!', description='```' + formatar_carrinho(estado['carrinho']) + '```', color=0x9B59B6)
                embed.set_footer(text='O que deseja fazer agora?')
                await message.channel.send(embed=embed, view=CarrinhoView())
            else:
                await message.channel.send('Digite um numero valido de quantidade! 😊', view=NavegacaoView())

        elif etapa == 'cupom':
            codigo = content.upper()
            if codigo in cupons_ativos:
                cupom = cupons_ativos[codigo]
                estado['cupom_usado'] = codigo
                txt, total_orig, total_final = formatar_carrinho_com_desconto(estado['carrinho'], cupom['desconto'], cupom['categoria'])
                estado['total_final'] = total_final
                estado['etapa'] = 'carrinho'
                embed = discord.Embed(title='🎁  Cupom Aplicado! ' + codigo, description='**' + str(cupom['desconto']) + '% de desconto** em ' + cupom['categoria'] + '!\n\n```' + txt + '```', color=0x57F287)
                await message.channel.send(embed=embed, view=CarrinhoView())
            else:
                estado['etapa'] = 'carrinho'
                await message.channel.send('❌ Cupom invalido ou expirado! Continuando sem desconto.', view=CarrinhoView())

        elif etapa in ['descricao', 'descricao_outro']:
            estado['descricao'] = content
            estado['etapa'] = 'confirmacao'
            total = estado.get('total_final') or calcular_total(estado['carrinho'])
            valor_txt = 'R$' + str(total) if total > 0 else 'A combinar com a equipe'
            embed = discord.Embed(title='📋  Resumo do Pedido', description='Confira tudo abaixo e confirme!', color=0x9B59B6)
            if estado['carrinho']:
                embed.add_field(name='🛒  Itens', value='```' + formatar_carrinho(estado['carrinho']) + '```', inline=False)
            embed.add_field(name='💰  Total', value=valor_txt, inline=True)
            if estado.get('cupom_usado'):
                embed.add_field(name='🎁  Cupom', value=estado['cupom_usado'], inline=True)
            embed.add_field(name='📝  Descricao', value=content, inline=False)
            embed.set_footer(text='Deseja confirmar o pedido?')
            await message.channel.send(embed=embed, view=ConfirmarPedidoView())

        elif etapa == 'aguardando_comprovante':
            if message.attachments:
                estado['etapa'] = 'finalizado'
                total = estado.get('total_final') or calcular_total(estado['carrinho'])
                pedidos_do_dia.append({'cliente': estado.get('cliente', str(message.author)), 'cliente_id': estado.get('cliente_id', message.author.id), 'itens': estado['carrinho'].copy(), 'descricao': estado['descricao'], 'total': total, 'horario': estado.get('horario', ''), 'ticket': message.channel.name, 'cupom': estado.get('cupom_usado', '')})
                embed_ok = discord.Embed(title='✅  Comprovante Recebido!', description='Obrigado! Seu comprovante foi enviado para nossa equipe.\n\nAssim que confirmarmos o pagamento, iniciaremos sua encomenda! 🚀', color=0x57F287)
                embed_ok.set_footer(text='BG Store - Obrigado pela preferencia!')
                await message.channel.send(embed=embed_ok)
                valor_txt = 'R$' + str(total) if total > 0 else 'A combinar'
                for uid in AUTHORIZED_USER_IDS:
                    user = message.guild.get_member(uid)
                    if user:
                        try:
                            embed_pv = discord.Embed(title='🛒  Novo Pedido - BG Store', description='Novo pedido com comprovante!', color=0x9B59B6)
                            embed_pv.add_field(name='👤  Cliente', value=str(message.author) + ' (' + str(message.author.id) + ')', inline=False)
                            if estado['carrinho']:
                                embed_pv.add_field(name='🛒  Itens', value='```' + formatar_carrinho(estado['carrinho']) + '```', inline=False)
                            embed_pv.add_field(name='💰  Total', value=valor_txt, inline=True)
                            if estado.get('cupom_usado'):
                                embed_pv.add_field(name='🎁  Cupom', value=estado['cupom_usado'], inline=True)
                            embed_pv.add_field(name='📝  Descricao', value=estado['descricao'], inline=False)
                            embed_pv.add_field(name='🔗  Ticket', value=message.channel.mention, inline=False)
                            embed_pv.set_footer(text='Verifique o comprovante!')
                            await user.send(embed=embed_pv)
                            await user.send(file=await message.attachments[0].to_file())
                        except Exception as e:
                            print('Erro PV: ' + str(e))
            else:
                await message.channel.send('Por favor, envie o **comprovante como imagem** aqui no chat! 📸')

    await bot.process_commands(message)


def is_authorized(interaction):
    return interaction.user.id in AUTHORIZED_USER_IDS


async def update_or_send_status(interaction, online):
    global status_message_id, loja_online
    loja_online = online
    guild = interaction.guild
    channel = guild.get_channel(STATUS_CHANNEL_ID)
    if channel is None:
        await interaction.response.send_message('Canal nao encontrado.', ephemeral=True)
        return
    embed = build_status_embed(online, guild)
    if status_message_id:
        try:
            msg = await channel.fetch_message(status_message_id)
            await msg.edit(embed=embed)
            await interaction.response.send_message('Status atualizado!', ephemeral=True)
            return
        except discord.NotFound:
            pass
    msg = await channel.send(embed=embed)
    status_message_id = msg.id
    await interaction.response.send_message('Loja definida!', ephemeral=True)


@tree.command(name='lojaon', description='Coloca a BG Store como ONLINE')
async def lojaon(interaction: discord.Interaction):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    await update_or_send_status(interaction, online=True)


@tree.command(name='lojaoff', description='Coloca a BG Store como OFFLINE')
async def lojaoff(interaction: discord.Interaction):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    await update_or_send_status(interaction, online=False)


@tree.command(name='status', description='Mostra o status atual da BG Store')
async def status_cmd(interaction: discord.Interaction):
    embed = build_status_embed(loja_online, interaction.guild)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name='atendimento', description='Envia o painel de atendimento com botao de ticket')
async def atendimento(interaction: discord.Interaction):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    embed = discord.Embed(title='🛒  BG Store - Atendimento', description='Clique no botao abaixo para abrir um ticket!\n\nFazemos **encomendas** de builds, scripts, mapas e muito mais para **Roblox Studio**.', color=0x9B59B6)
    embed.add_field(name='⚡  Diferenciais', value='✅ Entrega rapida\n✅ Fotos do andamento\n✅ Qualidade profissional\n✅ Precos acessiveis', inline=False)
    embed.set_footer(text='BG Store - Build • Script • Performance')
    await interaction.response.send_message(embed=embed, view=AbrirTicketView())


@tree.command(name='cardapio', description='Posta o cardapio de precos no canal de produtos')
async def cardapio(interaction: discord.Interaction):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    channel = interaction.guild.get_channel(CARDAPIO_CHANNEL_ID)
    if not channel:
        await interaction.response.send_message('Canal de cardapio nao encontrado!', ephemeral=True)
        return
    embed = build_cardapio_embed()
    await channel.send(embed=embed)
    await interaction.response.send_message('Cardapio postado! 🛒', ephemeral=True)


@tree.command(name='promocao', description='Cria uma promocao relampago para todos verem')
@app_commands.describe(titulo='Titulo da promocao', descricao='Descricao da oferta', duracao='Duracao em minutos')
async def promocao(interaction: discord.Interaction, titulo: str, descricao: str, duracao: int):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    expira = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))) + datetime.timedelta(minutes=duracao)
    promocoes_ativas[titulo] = {'descricao': descricao, 'expira': expira}
    embed = discord.Embed(title='⚡  PROMOCAO RELAMPAGO — ' + titulo, description=descricao, color=0xF1C40F)
    embed.add_field(name='⏰  Valida por', value=str(duracao) + ' minutos!', inline=True)
    embed.add_field(name='🛒  Como aproveitar?', value='Abra um ticket agora e informe a promocao!', inline=False)
    embed.set_footer(text='BG Store • Corra que e por tempo limitado!')
    guild = interaction.guild
    for channel in guild.text_channels:
        if channel.permissions_for(guild.default_role).read_messages:
            try:
                await channel.send('@everyone', embed=embed)
                break
            except:
                pass
    await interaction.response.send_message('Promocao criada e anunciada!', ephemeral=True)


@tree.command(name='cupom', description='Cria um cupom de desconto')
@app_commands.describe(codigo='Codigo do cupom (ex: BGSTORE10)', desconto='Porcentagem de desconto (ex: 10)', duracao='Duracao em minutos', categoria='Categoria do desconto (ex: Casas, Sedes, tudo)')
async def cupom(interaction: discord.Interaction, codigo: str, desconto: int, duracao: int, categoria: str):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    expira = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))) + datetime.timedelta(minutes=duracao)
    cupons_ativos[codigo.upper()] = {'desconto': desconto, 'categoria': categoria, 'expira': expira}
    embed = discord.Embed(title='🎁  Cupom Criado!', color=0x57F287)
    embed.add_field(name='Codigo', value='`' + codigo.upper() + '`', inline=True)
    embed.add_field(name='Desconto', value=str(desconto) + '%', inline=True)
    embed.add_field(name='Categoria', value=categoria, inline=True)
    embed.add_field(name='Valido por', value=str(duracao) + ' minutos', inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name='pedidos', description='Mostra os pedidos do dia')
async def pedidos(interaction: discord.Interaction):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    if not pedidos_do_dia:
        await interaction.response.send_message('Nenhum pedido hoje ainda!', ephemeral=True)
        return
    embed = discord.Embed(title='📦  Pedidos de Hoje', description='Total de **' + str(len(pedidos_do_dia)) + '** pedidos', color=0x9B59B6)
    for i, p in enumerate(pedidos_do_dia):
        valor = 'R$' + str(p['total']) if p['total'] > 0 else 'A combinar'
        embed.add_field(name='Pedido #' + str(i + 1) + ' - ' + p['horario'], value='👤 ' + p['cliente'] + '\n💰 ' + valor + '\n📝 ' + (p['descricao'][:50] + '...' if len(p['descricao']) > 50 else p['descricao']), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)
    for uid in AUTHORIZED_USER_IDS:
        user = interaction.guild.get_member(uid)
        if user and user.id != interaction.user.id:
            try:
                await user.send(embed=embed)
            except:
                pass


@tree.command(name='faturamento', description='Mostra o faturamento do dia')
async def faturamento(interaction: discord.Interaction):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    total_dia = sum(p['total'] for p in pedidos_do_dia)
    qtd = len(pedidos_do_dia)
    data_hoje = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).strftime('%d/%m/%Y')
    embed = discord.Embed(title='💰  Faturamento - ' + data_hoje, color=0x57F287)
    embed.add_field(name='📦  Total de Pedidos', value=str(qtd), inline=True)
    embed.add_field(name='💵  Total Faturado', value='R$' + str(total_dia), inline=True)
    embed.add_field(name='📊  Ticket Medio', value='R$' + str(round(total_dia / qtd, 2)) if qtd > 0 else 'R$0', inline=True)
    if pedidos_do_dia:
        mais_vendido = {}
        for p in pedidos_do_dia:
            for item in p['itens']:
                mais_vendido[item['nome']] = mais_vendido.get(item['nome'], 0) + item['qtd']
        if mais_vendido:
            top = max(mais_vendido, key=mais_vendido.get)
            embed.add_field(name='🏆  Mais Vendido', value=top + ' (' + str(mais_vendido[top]) + 'x)', inline=False)
    embed.set_footer(text='BG Store - Dados do dia atual')
    await interaction.response.send_message(embed=embed, ephemeral=True)
    for uid in AUTHORIZED_USER_IDS:
        user = interaction.guild.get_member(uid)
        if user and user.id != interaction.user.id:
            try:
                await user.send(embed=embed)
            except:
                pass


@tree.command(name='aceitar', description='Aceita o pedido do cliente no ticket')
@app_commands.describe(item='O que foi pedido (ex: Sede PM, Mapa Grande)', preco='Valor combinado em reais (ex: 30)')
async def aceitar(interaction: discord.Interaction, item: str, preco: str):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    if not interaction.channel.name.startswith('ticket-'):
        await interaction.response.send_message('Use este comando dentro de um ticket!', ephemeral=True)
        return
    embed = discord.Embed(title='✅  Pedido Aceito!', description='Seu pedido foi **aceito** pela equipe da BG Store!\n\nAssim que recebermos o pagamento, iniciamos a producao! 🚀', color=0x57F287)
    embed.add_field(name='📦  Item', value=item, inline=True)
    embed.add_field(name='💰  Valor', value='R$' + preco, inline=True)
    embed.add_field(name='🔑  Chave PIX', value='`' + PIX + '`', inline=False)
    embed.add_field(name='📸  Proximo passo', value='Faca o PIX e envie o **comprovante como imagem** aqui no ticket!', inline=False)
    embed.set_footer(text='BG Store - Obrigado pela preferencia!')
    await interaction.response.send_message(embed=embed)
    if interaction.channel.id in ticket_estado:
        ticket_estado[interaction.channel.id]['etapa'] = 'aguardando_comprovante'
        ticket_estado[interaction.channel.id]['descricao'] = item
    preco_int = int(preco) if preco.isdigit() else 0
    pedidos_do_dia.append({'cliente': interaction.channel.name, 'cliente_id': 0, 'itens': [{'nome': item, 'preco': preco_int, 'qtd': 1}], 'descricao': item, 'total': preco_int, 'horario': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).strftime('%d/%m/%Y %H:%M'), 'ticket': interaction.channel.name, 'cupom': ''})


@tree.command(name='recusar', description='Recusa o pedido do cliente no ticket')
@app_commands.describe(motivo='Motivo da recusa')
async def recusar(interaction: discord.Interaction, motivo: str):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    if not interaction.channel.name.startswith('ticket-'):
        await interaction.response.send_message('Use este comando dentro de um ticket!', ephemeral=True)
        return
    embed = discord.Embed(title='❌  Pedido Recusado', description='Infelizmente nao foi possivel aceitar seu pedido no momento.\n\n**Motivo:** ' + motivo + '\n\nSe tiver duvidas, entre em contato com nossa equipe!', color=0xED4245)
    embed.set_footer(text='BG Store - Agradecemos o contato!')
    await interaction.response.send_message(embed=embed)


@tree.command(name='emproducao', description='Avisa o cliente que o pedido esta em producao')
@app_commands.describe(previsao='Previsao de entrega (ex: 2 dias, 24 horas)')
async def emproducao(interaction: discord.Interaction, previsao: str):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    if not interaction.channel.name.startswith('ticket-'):
        await interaction.response.send_message('Use este comando dentro de um ticket!', ephemeral=True)
        return
    embed = discord.Embed(title='⚙️  Pedido em Producao!', description='Seu pedido esta sendo produzido com muito cuidado!\n\nVamos te mandar fotos do andamento em breve 📸', color=0xF1C40F)
    embed.add_field(name='⏰  Previsao de Entrega', value=previsao, inline=False)
    embed.set_footer(text='BG Store - Qualidade e capricho em cada detalhe!')
    await interaction.response.send_message(embed=embed)


@tree.command(name='entregue', description='Avisa o cliente que o pedido foi entregue')
async def entregue(interaction: discord.Interaction):
    if not is_authorized(interaction):
        await interaction.response.send_message('Voce nao tem permissao.', ephemeral=True)
        return
    if not interaction.channel.name.startswith('ticket-'):
        await interaction.response.send_message('Use este comando dentro de um ticket!', ephemeral=True)
        return
    embed = discord.Embed(title='📦  Pedido Entregue!', description='Seu pedido foi **entregue** com sucesso! 🎉\n\nEsperamos que tenha gostado! Se precisar de ajustes ou tiver duvidas, fale com a gente aqui no ticket.\n\n**Obrigado por escolher a BG Store!** 🟣', color=0x57F287)
    embed.set_footer(text='BG Store - Build • Script • Performance')
    await interaction.response.send_message(embed=embed)


bot.run(TOKEN)
