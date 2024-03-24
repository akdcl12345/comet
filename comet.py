# 모듈 불러오기
from code import interact
import nextcord, asyncio
from nextcord.ext import commands
import asyncio, string
import random
import toss, time
import json
import time
import re
import requests
from nextcord import SlashOption
import os
import datetime
import sqlite3
from itertools import islice
import ast
import io

# TOKEN = os.environ['TOKEN']
global on_run
on_run = True
SERVICE_NAME = "Comet"  # 서비스 이름
official_discord_server_link = "https://discord.gg/fJDuDRa2qf"  # 서비스 디스코드 서버
admin_ids = [1153283662570344538, 746534136210259989]  # 봇 관리 유저 아이디


def check(name, amount, guildid):
    conn = sqlite3.connect(f'SERVER/{guildid}.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS charge(
            id INTEGER PRIMARY KEY
        );
    ''')

    base = {"result": None, "id": None, "name": None, "amount": None, "msg": None}

    url = "https://api-public.toss.im/api-public/v3/cashtag/transfer-feed/received/list?inputWord=aus555"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"}
    response = requests.get(url, headers=headers).json()

    data = response["success"]["data"]
    for transaction in data:
        transfer_id = transaction["cashtagTransferId"]
        transfer_name = transaction["senderDisplayName"]
        transfer_amount = transaction["amount"]

        if name == transfer_name:  # 1. 이름이 동일한가?
            cur.execute('''
                SELECT id FROM charge WHERE id = ?;
            ''', (transfer_id,))
            checked = cur.fetchone()

            if not checked and amount == transfer_amount:  # 2. 이전에 처리되지 않은 기록인가? / 3. 금액이 동일한가?
                cur.execute('''
                    INSERT INTO charge (id) VALUES (?);
                ''', (transfer_id,))
                conn.commit()
                base["result"] = True
                base["id"] = transfer_id
                base["name"] = transfer_name
                base["amount"] = transfer_amount
                return base

    base["result"] = False  # 입금내역에 존재하지 않음
    base["msg"] = "입금 미확인"
    return base


# 봇 기본설정
class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.persistant_modals_added = False
        self.persistant_views_added = False

    async def on_ready(self):
        print(f"Comet | {self.user}으로 로그인됨 (ID: {self.user.id})")


# 접두사 설정
bot = Bot(command_prefix="!", intents=nextcord.Intents.all(), help_command=None)


# 시간설정
def convert_time(seconds):
    hours = minutes = 0
    if seconds >= 3600:
        hours, seconds = divmod(seconds, 3600)
    if seconds >= 60:
        minutes, seconds = divmod(seconds, 60)
    time_format = f"{hours}시간{minutes}분{seconds}초"
    return time_format


########################################################################################################################################

# 등록버튼
class SetupButton(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="다음", style=nextcord.ButtonStyle.blurple, custom_id="button_1")
    async def button_callback1(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(ServerSetup(self))


# 공지수정 모달
class EditNoticeModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(
            title="공지 수정",
            custom_id="editnotice",
            timeout=None
        )
        self.field = nextcord.ui.TextInput(
            label="수정할 공지 입력",
            required=True,
            style=nextcord.TextInputStyle.paragraph,
            custom_id="notice",
        )
        self.add_item(self.field)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        try:
            notice = self.children[0].value
            conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
            c = conn.cursor()
            data2 = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (interaction.guild.id,)).fetchone()
            if data2 is None:
                embed = nextcord.Embed(title="⛔ㆍ오류 발생", color=0xfffffe)
                embed.add_field(name="", value=f"오류가 발생했어요.", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                conn.close()
            else:
                c.execute("UPDATE serverinfo SET notice = ? WHERE serverid = ?",
                          (self.children[0].value, interaction.guild.id,))
                conn.commit()
                conn.close()
                embed = nextcord.Embed(title="✅ㆍ수정 완료", color=0xfffffe)
                embed.add_field(name="공지가 아래와 같이 수정되었어요.", value=self.children[0].value, inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(e)
            pass


# 공지 수정 명령어
class EditNotice(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="수정", emoji="✏️", style=nextcord.ButtonStyle.grey, custom_id="button_1")
    async def button_callback1(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(EditNoticeModal())


# 서버 제거 모달
class ServerDelModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(
            title="서버 제거",
            custom_id="delserver",
            timeout=None
        )
        self.field = nextcord.ui.TextInput(
            label="삭제할 서버 ID를 입력해주세요.",
            required=True,
            style=nextcord.TextInputStyle.short,
            custom_id="serverid",
        )
        self.add_item(self.field)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        try:
            serverid = int(self.children[0].value)
            conn = sqlite3.connect(f'DB/server.db')
            c = conn.cursor()
            data = c.execute("SELECT * FROM serverlist WHERE serverid = ?", (serverid,)).fetchone()
            if data is None:
                embed = nextcord.Embed(title="⛔ㆍ오류 발생", color=0xfffffe)
                embed.add_field(name="", value=f"존재하지 않는 서버에요.", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                conn.close()
            else:
                c.execute("DELETE FROM serverlist WHERE serverid=?", (serverid,))
                conn.commit()
                conn.close()
                embed = nextcord.Embed(title="✅ㆍ삭제 완료", color=0xfffffe)
                guild = bot.get_guild(serverid)
                embed.add_field(name=f"`{guild.name}` 서버가 삭제되었어요.", value="", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(e)
            pass


# 서버 제거 명령어
class ServerDel(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="제거", emoji="🗑️", style=nextcord.ButtonStyle.grey, custom_id="button_1")
    async def button_callback1(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(ServerDelModal())


# 서버 세팅 1
class CheckeLicense(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(
            title="라이센스 등록",
            custom_id="seteup",
            timeout=None
        )
        self.field = nextcord.ui.TextInput(
            label="구매하신 라이센스를 입력해주세요.",
            required=True,
            style=nextcord.TextInputStyle.short,
            custom_id="license",
        )
        self.add_item(self.field)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        try:
            license_key = self.children[0].value
            conn = sqlite3.connect(f'DB/license.db')
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS licenses (license TEXT PRIMARY KEY)")
            data = c.execute("SELECT * FROM licenses WHERE license = ?", (license_key,)).fetchone()
            if data is None:
                conn.close()
                embed = nextcord.Embed(title="⛔ㆍ라이센스 확인 실패", color=0xfffffe)
                embed.add_field(name="",
                                value=f"라이센스가 유효하지 않아요.\n라이센스 구매 문의는 [여기로]({official_discord_server_link}) 주세요!",
                                inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                c.execute("DELETE FROM licenses WHERE license=?", (license_key,))
                conn.commit()
                conn.close()
                embed = nextcord.Embed(title="📃ㆍ라이센스 확인 성공", color=0xfffffe)
                embed.add_field(name="", value=f"추가 설정을 위해 아래 버튼을 클릭해주세요.", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=False, view=SetupButton())
        except Exception as e:
            print(e)
            pass


# 서버 세팅 2
class ServerSetup(nextcord.ui.Modal):
    def __init__(self, setupbutton):

        super().__init__(
            title="서버 관련 설정",
            custom_id="seteup",
            timeout=None
        )
        self.field = nextcord.ui.TextInput(
            label="서버 ID",
            required=True,
            style=nextcord.TextInputStyle.short,
            min_length=15,
            max_length=25,
            custom_id="info0",
        )
        self.add_item(self.field)
        self.field = nextcord.ui.TextInput(
            label="서버 이름",
            required=True,
            style=nextcord.TextInputStyle.short,
            min_length=1,
            max_length=10,
            custom_id="info1",
        )
        self.add_item(self.field)
        self.field = nextcord.ui.TextInput(
            label="공지사항",
            required=True,
            style=nextcord.TextInputStyle.paragraph,
            custom_id="info2",
        )
        self.add_item(self.field)
        self.field = nextcord.ui.TextInput(
            label="서버 아이콘 URL",
            required=True,
            style=nextcord.TextInputStyle.paragraph,
            custom_id="info3",
            max_length="150"
        )
        self.add_item(self.field)
        self.field = nextcord.ui.TextInput(
            label="관리자 역할 ID",
            required=True,
            min_length=15,
            max_length=25,
            style=nextcord.TextInputStyle.short,
            custom_id="info4",
        )
        self.add_item(self.field)
        self.setupbutton = setupbutton

    async def callback(self, interaction: nextcord.Interaction) -> None:
        self.setupbutton.stop()
        try:
            info0 = self.children[0].value
            info1 = self.children[1].value
            info2 = self.children[2].value
            info3 = self.children[3].value
            info4 = self.children[4].value
            embed = nextcord.Embed(title="📃ㆍ설정 완료 [ 1 / 3 ]", color=0xfffffe)
            embed.add_field(name="", value=f"추가 설정을 위해 아래 버튼을 클릭해주세요.", inline=False)
            await interaction.response.send_message(embed=embed, view=SetupButton2(info0, info1, info2, info3, info4))
        except Exception as e:
            print(e)
            pass


# 서버 세팅 3
class SetupButton2(nextcord.ui.View):
    def __init__(self, info0, info1, info2, info3, info4):
        super().__init__(timeout=None)
        self.info0 = info0
        self.info1 = info1
        self.info2 = info2
        self.info3 = info3
        self.info4 = info4

    @nextcord.ui.button(label="다음", style=nextcord.ButtonStyle.blurple, custom_id="button_2")
    async def button_callback1(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        info0 = self.info0
        info1 = self.info1
        info2 = self.info2
        info3 = self.info3
        info4 = self.info4
        await interaction.response.send_modal(ServerSetup2(info0, info1, info2, info3, info4, self))


class ServerSetup2(nextcord.ui.Modal):
    def __init__(self, info0, info1, info2, info3, info4, setupbutton2):

        super().__init__(
            title="구매 관련 설정",
            custom_id="seteup2",
            timeout=None
        )
        self.field = nextcord.ui.TextInput(
            label="구매로그 채널 ID",
            required=True,
            min_length=15,
            max_length=25,
            style=nextcord.TextInputStyle.short,
            custom_id="info5",
        )
        self.add_item(self.field)
        self.field = nextcord.ui.TextInput(
            label="컬쳐랜드 아이디",
            required=True,
            min_length=5,
            max_length=15,
            style=nextcord.TextInputStyle.short,
            custom_id="info6",
        )
        self.add_item(self.field)
        self.field = nextcord.ui.TextInput(
            label="토스 ID 입력",
            min_length=5,
            max_length=12,
            required=True,
            style=nextcord.TextInputStyle.short,
            custom_id="info7",
        )
        self.add_item(self.field)
        self.field = nextcord.ui.TextInput(
            label="토스 ID 최소 충전금액",
            required=True,
            min_length=1,
            max_length=7,
            style=nextcord.TextInputStyle.short,
            custom_id="info8",
        )
        self.add_item(self.field)
        self.field = nextcord.ui.TextInput(
            label="컬쳐랜드 비밀번호",
            required=True,
            min_length=5,
            max_length=30,
            style=nextcord.TextInputStyle.short,
            custom_id="info9",
        )
        self.add_item(self.field)
        self.info0 = info0
        self.info1 = info1
        self.info2 = info2
        self.info3 = info3
        self.info4 = info4
        self.setupbutton2 = setupbutton2

    async def callback(self, interaction: nextcord.Interaction) -> None:
        try:
            self.setupbutton2.stop()
            info0 = self.info0
            info1 = self.info1
            info2 = self.info2
            info3 = self.info3
            info4 = self.info4
            info5 = self.children[0].value
            info6 = self.children[1].value
            if self.children[2].value is None:
                info7 = "None"
                info8 = "`토스ID 사용불가`"
            else:
                info7 = self.children[2].value
                if self.children[3].value is None:
                    info8 = "1"
                else:
                    info8 = self.children[3].value
            info9 = self.children[4].value
            embed = nextcord.Embed(title="📃ㆍ설정 완료 [ 2 / 3]", color=0xfffffe)
            embed.add_field(name="", value=f"추가 설정을 위해 아래 버튼을 클릭해주세요.", inline=False)
            await interaction.response.send_message(embed=embed,
                                                    view=SetCurrencyView(info0, info1, info2, info3, info4, info5,
                                                                         info6, info7, info8, info9))

        except Exception as e:
            print(e)
            pass


# 화폐 설정
class SetCurrency(nextcord.ui.Select):
    def __init__(self, info0, info1, info2, info3, info4, info5, info6, info7, info8, info9):
        super().__init__(custom_id='setupcurrency', placeholder='사용할 충전 방식을 선택해주세요.', min_values=1, max_values=2,
                         options=[
                             nextcord.SelectOption(label='토스아이디', description='토스아이디로 충전해요.', value='토스익명'),
                             nextcord.SelectOption(label='문화상품권', description='문화상품권으로 충전해요.', value=f'문화상품권')
                         ])
        self.info0 = info0
        self.info1 = info1
        self.info2 = info2
        self.info3 = info3
        self.info4 = info4
        self.info5 = info5
        self.info6 = info6
        self.info7 = info7
        self.info8 = info8
        self.info9 = info9

    async def callback(self, interaction: nextcord.Interaction):
        info0 = self.info0
        info1 = self.info1
        info2 = self.info2
        info3 = self.info3
        info4 = self.info4
        info5 = self.info5
        info6 = self.info6
        info7 = self.info7
        info8 = self.info8
        info9 = self.info9
        if len(self.values) > 1:
            info10 = f"{self.values[0]}, {self.values[1]}"
        else:
            info10 = self.values[0]
        embed = nextcord.Embed(title="📃ㆍ설정 완료 [ 3 / 3 ]", color=0xfffffe)
        embed.add_field(name=f"",
                        value=f"- 서버 ID : `{info0}`\n- 서버 이름 : `{info1}`\n- 서버공지 : `{info2}`\n- 서버 아이콘 URL : `생략`\n- 관리자 역할 ID : `{info4}`\n- 구매로그 채널 ID : `{info5}`\n- 컬쳐랜드 ID : `{info6}`\n- 토스 ID : `{info7}`\n- 최소충전금액 : `{info8}`\n- 컬쳐랜드PW : ||`{info9}`||\n- 충전 가능 통화 : `{info10}`",
                        inline=False)
        await interaction.response.send_message(embed=embed,
                                                view=SetupButton3(info0, info1, info2, info3, info4, info5, info6,
                                                                  info7, info8, info9, info10))


# 화폐 보기
class SetCurrencyView(nextcord.ui.View):
    def __init__(self, info0, info1, info2, info3, info4, info5, info6, info7, info8, info9):
        super().__init__(timeout=None)
        self.add_item(SetCurrency(info0, info1, info2, info3, info4, info5, info6, info7, info8, info9))


# 서버 세팅 4
class SetupButton3(nextcord.ui.View):
    def __init__(self, info0, info1, info2, info3, info4, info5, info6, info7, info8, info9, info10):
        super().__init__(timeout=None)
        self.info0 = info0
        self.info1 = info1
        self.info2 = info2
        self.info3 = info3
        self.info4 = info4
        self.info5 = info5
        self.info6 = info6
        self.info7 = info7
        self.info8 = info8
        self.info9 = info9
        self.info10 = info10

    @nextcord.ui.button(label="확인", emoji="✅", style=nextcord.ButtonStyle.blurple, custom_id="button_3")
    async def button_callback1(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        info0 = self.info0
        info1 = self.info1
        info2 = self.info2
        info3 = self.info3
        info4 = self.info4
        info5 = self.info5
        info6 = self.info6
        info7 = self.info7
        info8 = self.info8
        info9 = self.info9
        info10 = self.info10

        embed = nextcord.Embed(title="🎉ㆍ사장님의 시작을 응원합니다!", color=0xfffffe)
        embed.add_field(name="", value=f"등록이 완료되었어요.\n명령어는 `/도움말`을 참고해주세요.", inline=False)
        await interaction.response.send_message(embed=embed)

        conn = sqlite3.connect(f'DB/server.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS serverlist (serverid TEXT)")
        data = c.execute("SELECT * FROM serverlist WHERE serverid = ?", (interaction.guild.id,)).fetchone()

        if data is None:
            c.execute("INSERT INTO serverlist (serverid) VALUES (?)", (interaction.guild.id,))
            conn.commit()
            conn.close()
        conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS money (userid TEXT, useramount TEXT)")
        data = c.execute("SELECT * FROM money WHERE userid = ?", (interaction.user.id,)).fetchone()
        if data is None:
            c.execute("INSERT INTO money (userid, useramount) VALUES (?, ?)", (interaction.user.id, "0"))
        c.execute(
            "CREATE TABLE IF NOT EXISTS serverinfo (id INTEGER PRIMARY KEY,serverid TEXT,servername TEXT,notice TEXT,iconurl TEXT,adminroleid TEXT,purchaselogchannel TEXT,cultureid TEXT,tossid TEXT,mincharge TEXT,culturepw TEXT,currency TEXT, roleid INTERGER)")
        c.execute(
            "INSERT OR REPLACE INTO serverinfo (id, serverid,servername,notice,iconurl,adminroleid,purchaselogchannel,cultureid,tossid,mincharge,culturepw,currency) VALUES ((SELECT id FROM serverinfo WHERE id=1),?,?,?,?,?,?,?,?,?,?,?)",
            (info0, info1, info2, info3, info4, info5, info6, info7, info8, info9, info10))
        conn.commit()
        conn.close()
        self.stop()

    @nextcord.ui.button(label="취소", emoji="⛔", style=nextcord.ButtonStyle.blurple, custom_id="button_31")
    async def button_callback2(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        embed = nextcord.Embed(title="🔄️ㆍ재설정", color=0xfffffe)
        embed.add_field(name="", value=f"재설정하시려면 아래의 버튼을 클릭해주세요.", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=False, view=SetupButton())


###########################################################################################################################
# 구매 뷰
class ProductBuyView(nextcord.ui.View):
    def __init__(self, product_data, guilid):
        super().__init__(timeout=None)
        self.product_data = product_data
        self.guildid = guilid

    # 결제 시스템
    @nextcord.ui.button(emoji="✅", style=nextcord.ButtonStyle.blurple, custom_id="button_3_1")
    async def button_callback1(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        conn = sqlite3.connect(f'SERVER/{self.guildid}.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS money (userid INTEGER PRIMARY KEY,useramount INTEGER)")
        c.execute(
            "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY,title TEXT,description TEXT,price TEXT,invent INTEGER)")
        data = c.execute("SELECT * FROM money WHERE userid = ?", (interaction.user.id,)).fetchone()
        data2 = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (self.guildid,)).fetchone()

        if data is None:
            c.execute("INSERT INTO money (userid, useramount) VALUES (?, ?)", (interaction.user.id, "0"))
            data = c.execute("SELECT * FROM money WHERE userid = ?", (interaction.user.id,)).fetchone()
        if int(data[1]) >= int(self.product_data[2]):
            value = int(data[1]) - int(self.product_data[2])
            c.execute("UPDATE money SET useramount = ? WHERE userid = ?", (value, interaction.user.id))
            conn.commit()
            embed = nextcord.Embed(title="✅ㆍ구매 성공", color=0xfffffe)
            row = c.execute(f"SELECT * FROM {self.product_data[0]} LIMIT {int(self.product_data[1])}").fetchall()
            product_link = ""
            for rows in row:
                product_link += "- " + rows[1] + "\n"
            for rows in row:
                c.execute(f"DELETE FROM {self.product_data[0]} WHERE id = {rows[0]}")
            embed.add_field(name="제품", value=f"{product_link}", inline=False)
            embed.set_footer(text=f'Comet', icon_url=data2[4])
            embed.timestamp = datetime.datetime.now()
            await interaction.response.send_message(embed=embed, ephemeral=False)
            member = bot.get_guild(self.guildid).get_member(interaction.user.id)
            embedVar = nextcord.Embed(title=f"✅ㆍ구매 완료", color=0xfffffe)
            embedVar.add_field(name="",
                               value=f"<@{interaction.user.name}>님, **`{self.product_data[0] + self.product_data[1]}개`** 구매 감사합니다.",
                               inline=False)
            e_channel = bot.get_channel(int(data2[6]))
            await e_channel.send(embed=embedVar)

            role = bot.get_guild(int(data2[1])).get_role(data2[-1])
            await member.add_roles(role)

            self.stop()
            conn.commit()
            conn.close()

        elif int(data[1]) < int(self.product_data[1]):
            embed = nextcord.Embed(title="⛔ㆍ잔액 부족", color=0xff0000)
            embed.add_field(name="",
                            value=f"- 잔액이 부족해요.\n- **{interaction.user.name}**님의 잔액은 **{data[1]}**원 입니다.\n- 충전 후 다시 시도해주세요.",
                            inline=False)
            embed.set_footer(text=f'Comet', icon_url=data2[4])
            embed.timestamp = datetime.datetime.now()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            conn.close()

    @nextcord.ui.button(emoji="⛔", style=nextcord.ButtonStyle.blurple, custom_id="button_3_2")
    async def button_callback2(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        conn = sqlite3.connect(f'SERVER/{self.guildid}.db')
        c = conn.cursor()
        data2 = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (self.guildid,)).fetchone()
        conn.close()
        embed = nextcord.Embed(title="⛔ㆍ구매 취소", color=0xff0000)
        embed.add_field(name="", value="구매가 취소되었어요.", inline=False)
        embed.set_footer(text=f'Comet', icon_url=data2[4])
        embed.timestamp = datetime.datetime.now()
        await interaction.response.send_message(embed=embed, ephemeral=False)
        self.stop()


# 상품 설명
class ProductDescription(nextcord.ui.Select):
    def __init__(self, guilid):
        conn = sqlite3.connect(f'SERVER/{guilid}.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS money (userid INTEGER PRIMARY KEY,useramount INTEGER)")
        c.execute(
            "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY,title TEXT,description TEXT,price TEXT,invent INTEGER)")
        data = c.execute("SELECT * FROM products").fetchall()
        options = []
        for id, label_, desc, amount, invent in data:
            label = label_
            result = c.execute(f"SELECT COUNT(*) FROM {label}").fetchone()[0]
            c.execute(f"UPDATE products SET invent = ? WHERE id = ?", (int(result), id))
            conn.commit()
            description = ""
            value = id
            options.append(nextcord.SelectOption(label=label, description=description, value=value))
        conn.close()
        super().__init__(custom_id='my_dropdown2', placeholder='설명을 확인할 제품을 선택해주세요.', min_values=1, max_values=1,
                         options=options)

    # 구매
    async def callback(self, interaction: nextcord.Interaction):
        conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS money (userid INTEGER PRIMARY KEY,useramount INTEGER)")
        c.execute(
            "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY,title TEXT,description TEXT,price TEXT,invent INTEGER)")
        data = c.execute("SELECT * FROM products WHERE id = ?", (int(self.values[0]),)).fetchone()
        conn.close()
        await interaction.response.send_message(data[2], ephemeral=True)


# 제품 설명 보기
class ProductSearchView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="제품 설명", emoji="🔍", style=nextcord.ButtonStyle.blurple, custom_id="button_5_1")
    async def button_callback1(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_message(view=SelectDescription(interaction.guild.id), ephemeral=True)


# 제품 추가 모달
class ProductAddModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(
            title="상품 / 재고 추가",
            custom_id="product_add",
            timeout=None
        )

        self.field = nextcord.ui.TextInput(
            label="상품 / 재고 이름 입력",
            placeholder="제품 1",
            required=True,
            style=nextcord.TextInputStyle.short,
            custom_id="value_2_1",
        )
        self.add_item(self.field)
        self.field = nextcord.ui.TextInput(
            label="상품 / 재고 설명 입력",
            placeholder="이 제품은 00입니다.",
            required=True,
            style=nextcord.TextInputStyle.paragraph,
            custom_id="value_2_2",
        )
        self.add_item(self.field)
        self.field = nextcord.ui.TextInput(
            label="가격 입력",
            placeholder="12000",
            required=True,
            style=nextcord.TextInputStyle.short,
            custom_id="value_2_4",
        )
        self.add_item(self.field)
        self.field = nextcord.ui.TextInput(
            label="구매 시 제공할 상품 링크 / 텍스트",
            placeholder="https://google.com/",
            required=True,
            style=nextcord.TextInputStyle.short,
            custom_id="value_2_5",
        )
        self.add_item(self.field)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS money (userid INTEGER PRIMARY KEY,useramount INTEGER)")
        c.execute(
            "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY,title TEXT,description TEXT,price TEXT,invent INTEGER)")
        data = c.execute("SELECT * FROM products WHERE title = ?", (self.children[0].value,)).fetchone()
        if data is None:
            c.execute(f"CREATE TABLE IF NOT EXISTS {self.children[0].value} (id INTEGER PRIMARY KEY, value TEXT)")
            c.execute("INSERT INTO products (title, description, price, invent) VALUES (?, ?, ?,?)",
                      (self.children[0].value, self.children[1].value, self.children[2].value, 1))
        else:
            c.execute("UPDATE products SET invent = ? WHERE title = ?", (data[4] + 1, self.children[0].value))
        c.execute(f"INSERT INTO {self.children[0].value} (value) VALUES (?)", (self.children[3].value,))
        conn.commit()
        conn.close()
        await interaction.response.send_message("✅ㆍ제품이 추가되었어요.", ephemeral=True)


# 토스아이디 자동충전 [리퀘스트]
class rPwhkdlcp(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(
            title="토스아이디 충전",
            custom_id="product_add",
            timeout=None
        )

        self.field = nextcord.ui.TextInput(
            label="입금자명",
            required=True,
            style=nextcord.TextInputStyle.short,
            custom_id="value_6_1",
        )
        self.add_item(self.field)
        self.field = nextcord.ui.TextInput(
            label="충전(입금)할 금액",
            required=True,
            style=nextcord.TextInputStyle.short,
            custom_id="value_6_2",
        )
        self.add_item(self.field)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
        c = conn.cursor()
        data = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (interaction.guild.id,)).fetchone()
        conn.close()
        if int(self.children[1].value) < int(data[9]):
            await interaction.response.send_message(f"충전 최소금액은 {data[9]}원입니다.", ephemeral=True)
            return
        res = check(self.children[0].value, int(self.children[1].value), interaction.guild.id)
        if res["result"] == True:
            conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS money (userid INTEGER PRIMARY KEY,useramount INTEGER)")
            c.execute(
                "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY,title TEXT,description TEXT,price TEXT,invent INTEGER)")
            data = c.execute("SELECT * FROM money WHERE userid = ?", (interaction.user.id,)).fetchone()
            if data is None:
                c.execute("INSERT INTO money (userid, useramount) VALUES (?, ?)", (interaction.user.id, "0"))
                data = c.execute("SELECT * FROM money WHERE userid = ?", (interaction.user.id,)).fetchone()
            value_ = int(data[1]) + int(self.children[1].value)
            c.execute("UPDATE money SET useramount = ? WHERE userid = ?", (value_, interaction.user.id))
            conn.commit()
            data = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (interaction.guild.id,)).fetchone()
            conn.close()
            await interaction.response.send_message("충전이 완료되었어요.", ephemeral=True)

        else:
            await interaction.response.send_message(f"충전에 실패했어요.\n사유 : **`{res['msg']}`**", ephemeral=True)


# 계좌자충 뷰
class StartCharge(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="입금 완료", style=nextcord.ButtonStyle.blurple, custom_id="button_5_4")
    async def button_callback1(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(rPwhkdlcp())


# 화폐 선택 뷰
class SelectCharge(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="토스아이디", style=nextcord.ButtonStyle.blurple, custom_id="toss")
    async def button_callback0(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
        c = conn.cursor()
        data = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (interaction.guild.id,)).fetchone()
        conn.close()
        embed = nextcord.Embed(title="[ 토스아이디 입금 안내 ]", color=0xfffffe)
        embed.add_field(name="", value=f"충전을 하시려면 [여기](https://toss.me/{data[8]})를 눌러 입금 후, 입금정보를 제출해주세요.",
                        inline=False)
        embed.add_field(name="", value=f"최소 충전 금액은 {data[9]}원이에요.", inline=False)
        await interaction.response.send_message(embed=embed, view=StartCharge(), ephemeral=True)

    @nextcord.ui.button(label="문화상품권", style=nextcord.ButtonStyle.blurple, custom_id="culture")
    async def button_callback2(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(anstkd())


# 제품 조회 뷰
class ProductListView(nextcord.ui.View):
    def __init__(self):

        super().__init__(timeout=None)

    @nextcord.ui.button(label="공지", style=nextcord.ButtonStyle.blurple, custom_id="button_4_0")
    async def button_callback0(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if on_run:
            conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
            c = conn.cursor()
            data = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (interaction.guild.id,)).fetchone()
            conn.close()
            embed = nextcord.Embed(title="공지사항", color=0xfffffe)
            embed.add_field(name="", value=data[3], inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @nextcord.ui.button(label="상품", style=nextcord.ButtonStyle.blurple, custom_id="button_4_1")
    async def button_callback1(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS money (userid INTEGER PRIMARY KEY,useramount INTEGER)")
        c.execute(
            "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY,title TEXT,description TEXT,price TEXT,invent INTEGER)")
        data = c.execute("SELECT * FROM products").fetchall()
        options = []
        for id, label, desc, amount, invent in data:
            c.execute(f"CREATE TABLE IF NOT EXISTS {label} (id INTEGER PRIMARY KEY, value TEXT)")
            result = c.execute(f"SELECT COUNT(*) FROM {label}").fetchone()[0]
            c.execute(f"UPDATE products SET invent = ? WHERE title = ?", (int(result), id))
            conn.commit()
            options.append((id, label, amount, result))  # 각 요소를 튜플로 저장

        sorted_options = [f"{id} : {label}" for id, label, _, _ in options]
        output = "\n".join(sorted_options)

        self.options = output
        if on_run:
            conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
            c = conn.cursor()
            data = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (interaction.guild.id,)).fetchone()
            conn.close()
            embed = nextcord.Embed(title=f"{data[2]}ㆍ상품 목록", color=0xfffffe)

            for option in options:
                id, label, amount, result = option  # 튜플의 각 요소를 변수에 할당
                field_name = f"{id}ㆍ{label}"
                field_value = f" - {amount}원\n- 재고 {result}개"
                embed.add_field(name=field_name, value=field_value, inline=False)

            await interaction.response.send_message(embed=embed, view=ProductSearchView(), ephemeral=True)

    @nextcord.ui.button(label="구매", style=nextcord.ButtonStyle.blurple, custom_id="button_4_2")
    async def button_callback2(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if on_run:
            await interaction.response.send_message(view=ProductSelectView(interaction.guild.id), ephemeral=True)

    @nextcord.ui.button(label="충전", style=nextcord.ButtonStyle.blurple, custom_id="button_4_4")
    async def button_callback4(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if on_run:
            conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
            c = conn.cursor()
            data = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (interaction.guild.id,)).fetchone()
            conn.close()
            if data[11] == "토스아이디":
                embed = nextcord.Embed(title="토스아이디 입금 안내", color=0xfffffe)
                embed.add_field(name="", value=f"충전을 하시려면 [여기](https://toss.me/{data[8]})를 눌러 입금 후, 입금정보를 제출해주세요.",
                                inline=False)
                embed.add_field(name="", value=f"최소 충전 금액은 {data[9]}원이에요.", inline=False)
                await interaction.response.send_message(embed=embed, view=StartCharge(), ephemeral=True)
            elif data[11] == "문화상품권":
                await interaction.response.send_modal(anstkd())
            elif data[11] == "토스익명, 문화상품권" or "문화상품권, 토스익명":
                await interaction.response.send_message(view=SelectCharge(), ephemeral=True)

    @nextcord.ui.button(label="잔액", style=nextcord.ButtonStyle.blurple, custom_id="button_4_3")
    async def button_callback3(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if on_run:
            embed = nextcord.Embed(title=f"💸ㆍ잔액", color=0xfffffe)
            conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS money (userid INTEGER PRIMARY KEY,useramount INTEGER)")
            c.execute(
                "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY,title TEXT,description TEXT,price TEXT,invent INTEGER)")
            data = c.execute("SELECT * FROM money WHERE userid = ?", (interaction.user.id,)).fetchone()
            conn.close()
            if data is None:
                c.execute("INSERT INTO money (userid, useramount) VALUES (?, ?)", (interaction.user.id, "0"))
                data = c.execute("SELECT * FROM money WHERE userid = ?", (interaction.user.id,)).fetchone()

            embed.add_field(name="", value=f"- 이름 : **{interaction.user.name}**\n- 잔액 : **{data[1]}원**", inline=True)
            embed.set_thumbnail(interaction.user.display_avatar)
            await interaction.response.send_message(embed=embed, ephemeral=True)


# 제품 설명 선택
class SelectDescription(nextcord.ui.View):
    def __init__(self, guilid):
        super().__init__(timeout=None)
        self.add_item(ProductDescription(guilid))


# 제품 선택
class ProductSelectView(nextcord.ui.View):
    def __init__(self, guilid):
        super().__init__(timeout=None)
        self.add_item(ProductSelectSelect(guilid))


# 제품 선택 2
class ProductSelectSelect(nextcord.ui.Select):
    def __init__(self, guilid):
        conn = sqlite3.connect(f'SERVER/{guilid}.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS money (userid INTEGER PRIMARY KEY,useramount INTEGER)")
        c.execute(
            "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY,title TEXT,description TEXT,price TEXT,invent INTEGER)")
        data = c.execute("SELECT * FROM products").fetchall()
        options = []
        for id, label_, desc, amount, invent in data:
            label = label_
            result = c.execute(f"SELECT COUNT(*) FROM {label}").fetchone()[0]
            c.execute(f"UPDATE products SET invent = ? WHERE id = ?", (int(result), id))
            conn.commit()
            description = f"{amount}원ㅣ재고 {result}개"
            value = id
            options.append(nextcord.SelectOption(label=label, description=description, value=value))
        conn.close()
        super().__init__(custom_id='my_dropdown', placeholder='구매하실 제품을 선택해주세요.', min_values=1, max_values=1,
                         options=options)

    # 구매
    async def callback(self, interaction: nextcord.Interaction):
        conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS money (userid INTEGER PRIMARY KEY,useramount INTEGER)")
        c.execute(
            "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY,title TEXT,description TEXT,price TEXT,invent INTEGER)")
        data = c.execute("SELECT * FROM products WHERE id = ?", (int(self.values[0]),)).fetchone()
        if data[4] == 0:
            await interaction.response.send_message("재고가 부족해요.", ephemeral=True)
            conn.close()
            return
        conn.close()
        await interaction.response.send_modal(PurChaseInfo(data[1], data[4]))


# 구매 설정
class PurChaseInfo(nextcord.ui.Modal):
    def __init__(self, product_title, invent):
        super().__init__(
            title=f"{product_title}ㆍ제품 구매",
            custom_id="purchase",
            timeout=None
        )
        self.field = nextcord.ui.TextInput(
            label="구매할 수량을 입력해주세요.",
            required=True,
            style=nextcord.TextInputStyle.short,
            custom_id="amont",
        )
        self.add_item(self.field)

        self.product_title = product_title
        self.invent = invent

    async def callback(self, interaction: nextcord.Interaction) -> None:
        try:
            amount = int(self.children[0].value)
        except Exception as e:
            await interaction.response.send_message(f"정확한 수량을 입력해주세요.\n입력 : {self.children[0].value}", ephemeral=True)
            pass
            return
        if self.invent < amount:
            await interaction.response.send_message("⛔ㆍ재고가 부족해요.", ephemeral=True)
            return
        conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS money (userid INTEGER PRIMARY KEY,useramount INTEGER)")
        c.execute(
            "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY,title TEXT,description TEXT,price TEXT,invent INTEGER)")
        data = c.execute("SELECT * FROM products WHERE title = ?", (self.product_title,)).fetchone()

        embed = nextcord.Embed(title="구매 확인", color=0xfffffe)
        total_price = int(data[3]) * amount
        name_string = f"{data[1]} {str(amount)}개"
        embed.add_field(name=f"`{name_string}` - **{total_price}원**", value="", inline=False)
        data = c.execute("SELECT * FROM money WHERE userid = ?", (interaction.user.id,)).fetchone()
        embed.add_field(name="구매하시겠습니까?", value=f"- **{interaction.user.name}**님은 **{data[1]}원** 보유중 입니다.",
                        inline=False)
        data = c.execute("SELECT * FROM products WHERE title = ?", (self.product_title,)).fetchone()
        conn.close()
        product_data = [data[1], str(amount), total_price]  # 제목, 구매갯수, 총가격
        await interaction.user.send(embed=embed,
                                    view=ProductBuyView(product_data, interaction.guild.id))
        await interaction.response.send_message("💬ㆍDM을 확인해주세요.", ephemeral=True)


# 문화상퓸권 자동충전 [리퀘스트]
class anstkd(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(
            title=f"문화상품권 충전",
            custom_id="purchase",
            timeout=None
        )
        self.field = nextcord.ui.TextInput(
            label="상품권 핀번호를 입력해주세요. (-포함)",
            required=True,
            style=nextcord.TextInputStyle.short,
            custom_id="value",
        )
        self.add_item(self.field)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
        c = conn.cursor()
        data = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (str(interaction.guild.id),)).fetchone()
        data2 = {
            'token': '00000000-0000-0000-0000-000000000000',
            'id': data[7],
            'password': data[10],
            'pin': self.children[0].value
        }
        res_data = requests.post("", json=data2).json()
        if res_data["result"]:
            amount = int(res_data["amount"])
            data = c.execute("SELECT * FROM money WHERE userid = ?", (interaction.user.id,)).fetchone()
            if data:
                current_amount = int(data[1])
                updated_amount = current_amount + amount
                c.execute("UPDATE money SET useramount = ? WHERE userid = ?", (updated_amount, interaction.user.id,))
            else:
                c.execute("INSERT INTO money (userid, useramount) VALUES (?, ?)", (interaction.user.id, amount,))
            conn.commit()
            conn.close()
            embed = nextcord.Embed(title="✅ㆍ충전 성공", color=0xfffffe)
            embed.add_field(name=f"`{updated_amount}`원 충전에 성공했어요!", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            conn.close()
            embed = nextcord.Embed(title="⛔ㆍ충전 실패", color=0xfffffe)
            embed.add_field(name=f"`충전에 실패했어요.", inline=False)
            embed.add_field(name=f"`핀 번호를 다시 확인해주세요.", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.slash_command(name="자판기", description=f"{SERVICE_NAME} | 자동판매기를 세팅합니다.")
async def callback(interaction: nextcord.Interaction):
    if on_run:
        conn = sqlite3.connect(f'DB/server.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS serverlist (serverid TEXT)")
        data = c.execute("SELECT * FROM serverlist WHERE serverid = ?", (interaction.guild.id,)).fetchone()
        conn.close()
        if data is None:
            embed = nextcord.Embed(title="⛔ㆍ사용불가", color=0xfffffe)
            embed.add_field(name=f"{interaction.guild.name}",
                            value=f"이 서버는 {SERVICE_NAME}에 가입되지 않았어요.\n`/등록` 명령어로 서비스에 가입해주세요.", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
            c = conn.cursor()
            data = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (interaction.guild.id,)).fetchone()
            conn.close()
            if data is None:
                embed = nextcord.Embed(title="⛔ㆍ오류 발생", color=0xfffffe)
                embed.add_field(name="", value=f"오류가 발생했어요.", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            elif int(data[5]) in [role.id for role in interaction.user.roles]:
                embed = nextcord.Embed(title=data[2], description="원하시는 버튼을 클릭해주세요.", color=0xfffffe)
                await interaction.response.send_message(embed=embed, view=ProductListView())


@bot.slash_command(name="공지수정", description=f"{SERVICE_NAME} | 공지를 수정합니다.")
async def callback(interaction: nextcord.Interaction):
    if on_run:
        conn = sqlite3.connect(f'DB/server.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS serverlist (serverid TEXT)")
        data = c.execute("SELECT * FROM serverlist WHERE serverid = ?", (interaction.guild.id,)).fetchone()
        conn.close()
        if data is None:
            embed = nextcord.Embed(title="⛔ㆍ사용불가", color=0xfffffe)
            embed.add_field(name=f"{interaction.guild.name}",
                            value=f"이 서버는 {SERVICE_NAME}에 가입되지 않았어요.\n`/등록` 명령어로 서비스에 가입해주세요.", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
            c = conn.cursor()
            data = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (interaction.guild.id,)).fetchone()
            conn.close()
            if data is None:
                embed = nextcord.Embed(title="⛔ㆍ오류 발생", color=0xfffffe)
                embed.add_field(name="", value=f"오류가 발생했어요.", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            elif int(data[5]) in [role.id for role in interaction.user.roles]:
                embed = nextcord.Embed(title="📢ㆍ공지수정", color=0xfffffe)
                embed.add_field(name="현재 공지", value=f"```{data[3]}```", inline=False)
                await interaction.response.send_message(embed=embed, view=EditNotice())


# 서버 정보 커맨드
@bot.slash_command(name="정보", description=f"{SERVICE_NAME} | 서버 정보를 확인합니다.")
async def callback(interaction: nextcord.Interaction):
    if on_run:
        conn = sqlite3.connect(f'DB/server.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS serverlist (serverid TEXT)")
        data = c.execute("SELECT * FROM serverlist WHERE serverid = ?", (interaction.guild.id,)).fetchone()
        conn.close()
        if data is None:
            embed = nextcord.Embed(title="⛔ㆍ사용 불가", color=0xfffffe)
            embed.add_field(name=f"{interaction.guild.name}",
                            value=f"이 서버는 {SERVICE_NAME}에 가입되지 않았어요.\n`/등록` 명령어로 서비스에 가입해주세요.", inline=False, )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
            c = conn.cursor()
            data = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (interaction.guild.id,)).fetchone()
            conn.close()

            if data is None:
                embed = nextcord.Embed(title="⛔ㆍ오류 발생", color=0xfffffe)
                embed.add_field(name="", value=f"오류가 발생했어요.", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)

            elif int(data[5]) in [role.id for role in interaction.user.roles]:
                embed = nextcord.Embed(title=f"📄ㆍ{interaction.guild.name}", color=0xfffffe)
                embed.add_field(name=f" ",
                                value=f"**서버 ID** : `{data[1]}`\n**서버 이름** : `{data[2]}`\n**관리자** : <@&{data[5]}>\n**구매 로그** : <#{data[6]}>\n**컬쳐랜드 ID** : `{data[7]}`\n**컬쳐랜드 비밀번호** : || {data[10]}|| \n**토스 ID** : `{data[8]}`\n**최소충전금** : `{data[9]}원`\n**결제 수단** : `{data[11]}`",
                                inline=False)
                embed.set_thumbnail(data[4])
                await interaction.response.send_message(embed=embed, ephemeral=True)


# 도움말 커맨드
@bot.slash_command(name="도움말", description=f"{SERVICE_NAME} | 명령어 리스트를 확인합니다.")
async def callback(interaction: nextcord.Interaction):
    if on_run:
        conn = sqlite3.connect(f'DB/server.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS serverlist (serverid TEXT)")
        data = c.execute("SELECT * FROM serverlist WHERE serverid = ?", (interaction.guild.id,)).fetchone()
        conn.close()
        if data is None:
            embed = nextcord.Embed(title="⛔ㆍ사용 불가", color=0xfffffe)
            embed.add_field(name=f"{interaction.guild.name}",
                            value=f"이 서버는 {SERVICE_NAME}에 가입되지 않았어요.\n`/등록` 명령어로 서비스에 가입해주세요.", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
            c = conn.cursor()
            data = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (interaction.guild.id,)).fetchone()
            conn.close()
            if data is None:
                embed = nextcord.Embed(title="⛔ㆍ오류 발생", color=0xfffffe)
                embed.add_field(name="", value=f"오류가 발생했어요.", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            elif int(data[5]) in [role.id for role in interaction.user.roles]:
                embed = nextcord.Embed(title=f"📄ㆍ명령어", color=0xfffffe)
                embed.add_field(name=f"슬래시 명령어",
                                value=f"- `/등록`\n - 서버 등록 작업을 시작해요.\n- `/설정`\n - 서버 정보를 재설정해요.\n- `/정보`\n - 서버 정보를 확인해요.\n- `/자판기`\n - 자동판매기를 세팅해요.\n- `/잔액관리`\n - 유저 잔액을 관리해요.\n- `/재고추가`\n - 상품이나 재고를 추가해요.\n- `/재고삭제`\n - 상품이나 재고를 제거해요.\n `/공지수정`\n - 서버 공지를 수정해요.",
                                inline=False)
                embed.add_field(name=f"서포트 서버 방문하기", value=f"- https://cometkr.vercel.app/discord", inline=False)
                embed.add_field(name=f"자세한 도움말 확인하기", value=f"- 준비중", inline=False)
                embed.set_thumbnail(data[4])
                await interaction.response.send_message(embed=embed, ephemeral=True)


# 등록 커맨드
@bot.slash_command(name="등록", description=f"{SERVICE_NAME} | 자동판매 서비스를 등록합니다.")
async def callback(interaction: nextcord.Interaction):
    await interaction.response.send_modal(CheckeLicense())


# 잔액 관리 커맨드
@bot.slash_command(name="잔액관리", description=f"{SERVICE_NAME} | 유저 잔액을 관리합니다.")
async def callback(interaction: nextcord.Interaction, 멤버: nextcord.Member, 금액: str, 선택: str = SlashOption(
    description="추가 혹은 차감",
    required=True,
    choices=["추가", "차감"])):
    if on_run:
        conn = sqlite3.connect(f'DB/server.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS serverlist (serverid TEXT)")
        data = c.execute("SELECT * FROM serverlist WHERE serverid = ?", (interaction.guild.id,)).fetchone()
        conn.close()
        if data is None:
            embed = nextcord.Embed(title="⛔ㆍ사용불가", color=0xfffffe)
            embed.add_field(name=f"{interaction.guild.name}",
                            value=f"이 서버는 {SERVICE_NAME}에 가입되지 않았어요.\n`/등록` 명령어로 서비스에 가입해주세요.", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
            c = conn.cursor()
            data = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (interaction.guild.id,)).fetchone()
            conn.close()
            if data is None:
                embed = nextcord.Embed(title="⛔ㆍ오류 발생", color=0xfffffe)
                embed.add_field(name="", value=f"오류가 발생했어요.", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            elif int(data[5]) in [role.id for role in interaction.user.roles]:
                try:
                    userid = 멤버.id
                    select_user = await bot.fetch_user(userid)
                except Exception as e:
                    await interaction.response.send_message(f"사용자 id를 확인해주세요", ephemral=True)
                if select_user:
                    conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
                    c = conn.cursor()
                    c.execute("CREATE TABLE IF NOT EXISTS money (userid INTEGER PRIMARY KEY,useramount INTEGER)")
                    c.execute(
                        "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY,title TEXT,description TEXT,price TEXT,invent INTEGER)")
                    data = c.execute("SELECT * FROM money WHERE userid = ?", (select_user.id,)).fetchone()
                    if data is None:
                        c.execute("INSERT INTO money (userid, useramount) VALUES (?, ?)", (select_user.id, "0"))
                        data = c.execute("SELECT * FROM money WHERE userid = ?", (select_user.id,)).fetchone()
                    if 선택 == "추가":
                        value = int(data[1]) + int(금액)
                        c.execute("UPDATE money SET useramount = ? WHERE userid = ?", (value, select_user.id))
                        conn.commit()
                        conn.close()
                        await interaction.response.send_message(f"**{select_user.name}**에게 {금액}원을 지급하였습니다.")
                    elif 선택 == "차감":
                        value = int(data[1]) - int(금액)
                        c.execute("UPDATE money SET useramount = ? WHERE userid = ?", (value, select_user.id))
                        conn.commit()
                        conn.close()
                        await interaction.response.send_message(f"**{select_user.name}**에게 {금액}원을 차감하였습니다.")
            else:
                await interaction.response.send_message(f"⛔ㆍ명령어 사용 권한이 없어요.", ephemeral=True)


# 잔액확인 커맨드
# 추후 전체 잔액 확인 커맨드로 바뀔 예정
@bot.slash_command(name="잔액", description=f"{SERVICE_NAME} | 보유 잔액을 확인합니다.")
async def callback(interaction: nextcord.Interaction):
    if on_run:
        conn = sqlite3.connect(f'DB/server.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS serverlist (serverid TEXT)")
        data = c.execute("SELECT * FROM serverlist WHERE serverid = ?", (interaction.guild.id,)).fetchone()
        conn.close()
        if data is None:
            embed = nextcord.Embed(title="⛔ㆍ사용 불가", color=0xfffffe)
            embed.add_field(name=f"{interaction.guild.name}",
                            value=f"이 서버는 {SERVICE_NAME}에 가입되지 않았어요.\n`/등록` 명령어로 서비스에 가입해주세요.", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS money (userid INTEGER PRIMARY KEY,useramount INTEGER)")
            c.execute(
                "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY,title TEXT,description TEXT,price TEXT,invent INTEGER)")
            data = c.execute("SELECT * FROM money WHERE userid = ?", (interaction.user.id,)).fetchone()
        if data is None:
            c.execute("INSERT INTO money (userid, useramount) VALUES (?, ?)", (interaction.user.id, "0"))
            data = c.execute("SELECT * FROM money WHERE userid = ?", (interaction.user.id,)).fetchone()
        embed = nextcord.Embed(title="💸ㆍ잔액", color=0xfffffe)
        embed.add_field(name="", value=f"{interaction.user.name}님은 **{data[1]}원**을 보유하고 있어요.", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        conn.close()


# 제품추가 커맨드
@bot.slash_command(name="재고추가", description=f"{SERVICE_NAME} | 상품/재고를 추가합니다.")
async def callback(interaction: nextcord.Interaction):
    if on_run:
        conn = sqlite3.connect(f'DB/server.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS serverlist (serverid TEXT)")
        data = c.execute("SELECT * FROM serverlist WHERE serverid = ?", (interaction.guild.id,)).fetchone()
        conn.close()
        if data is None:
            embed = nextcord.Embed(title="⛔ㆍ사용 불가", color=0xfffffe)
            embed.add_field(name=f"{interaction.guild.name}",
                            value=f"이 서버는 {SERVICE_NAME}에 가입되지 않았어요.\n`/등록` 명령어로 서비스에 가입해주세요.", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
            c = conn.cursor()
            data = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (interaction.guild.id,)).fetchone()
            conn.close()
            if data is None:
                embed = nextcord.Embed(title="⛔ㆍ오류 발생", color=0xfffffe)
                embed.add_field(name="", value=f"오류가 발생했어요.", inline=False, ephemeral=True)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            elif int(data[5]) in [role.id for role in interaction.user.roles]:
                await interaction.response.send_modal(ProductAddModal())
            else:
                await interaction.response.send_message(f"⛔ㆍ명령어 사용 권한이 없어요.", ephemeral=True)


# 제품제거 커맨드
@bot.slash_command(name="재고삭제", description=f"{SERVICE_NAME} | 재고를 삭제합니다.")
async def callback(interaction: nextcord.Interaction, 제품번호: int = SlashOption(description="제품번호 입력", required=True)):
    if on_run:
        conn = sqlite3.connect(f'DB/server.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS serverlist (serverid TEXT)")
        data = c.execute("SELECT * FROM serverlist WHERE serverid = ?", (interaction.guild.id,)).fetchone()
        conn.close()
        if data is None:
            embed = nextcord.Embed(title="⛔ㆍ사용불가", color=0xfffffe)
            embed.add_field(name=f"{interaction.guild.name}",
                            value=f"이 서버는 {SERVICE_NAME}에 가입되지 않았어요.\n`/등록` 명령어로 서비스에 가입해주세요.", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
            c = conn.cursor()
            data = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (interaction.guild.id,)).fetchone()
            conn.close()
            if data is None:
                embed = nextcord.Embed(title="⛔ㆍ오류 발생", color=0xfffffe)
                embed.add_field(name="", value=f"오류가 발생했어요.", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            elif int(data[5]) in [role.id for role in interaction.user.roles]:
                conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
                c = conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS money (userid INTEGER PRIMARY KEY,useramount INTEGER)")
                c.execute(
                    "CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY,title TEXT,description TEXT,price TEXT,invent INTEGER)")
                data = c.execute("SELECT * FROM products WHERE id = ?", (제품번호,)).fetchone()
                if data is not None:
                    c.execute(f"DROP TABLE IF EXISTS {data[1]}")
                    c.execute("DELETE FROM products WHERE id = ?", (제품번호,))
                    conn.close()
                    await interaction.response.send_message("`✅ㆍ제품이 제거되었어요.`", ephemeral=True)
                else:
                    conn.close()
                    await interaction.response.send_message(f"제품번호 `{제품번호}`번은 존재하지 않아요.", ephemeral=True)
            else:
                await interaction.response.send_message(f"⛔ㆍ명령어 사용 권한이 없어요.", ephemeral=True)


@bot.slash_command(name='구매자', description='구매자 역할을 지정합니다.')
async def 역할(ctx: commands.Context, role: nextcord.Role):
    if ctx.user.guild_permissions.administrator:
        conn = sqlite3.connect(f'DB/server.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS serverlist (serverid TEXT)")
        data = c.execute("SELECT * FROM serverlist WHERE serverid = ?", (ctx.guild.id,)).fetchone()
        conn.close()
        if data is None:
            embed = nextcord.Embed(title="⛔ㆍ사용불가", color=0xfffffe)
            embed.add_field(name=f"{ctx.guild.name}",
                            value=f"이 서버는 {SERVICE_NAME}에 가입되지 않았어요.\n`/등록` 명령어로 서비스에 가입해주세요.", inline=False)
            await ctx.response.send_message(embed=embed, ephemeral=True)

        else:
            mentioned_role_id = role.id
            mentioned_role_id = int(mentioned_role_id)
            role_info = ctx.guild.get_role(mentioned_role_id)
            if (role_info == None):
                embed = nextcord.Embed(title="⛔ㆍ사용 불가", color=0xfffffe)
                embed.add_field(name=f"{ctx.guild.name}({ctx.guild.id})",
                                value=f"존재하지 않는 역할이에요.", inline=False)

                await ctx.response.send_message(embed=embed, ephemeral=True)
                return
            conn = sqlite3.connect(f'SERVER/{ctx.guild.id}.db')
            c = conn.cursor()
            c.execute("UPDATE serverinfo SET roleid = ? WHERE serverid == ?;", (mentioned_role_id, ctx.guild.id))
            conn.commit()
            conn.close()
            embed = nextcord.Embed(title="✅ㆍ수정 완료", color=0xfffffe)
            embed.add_field(name=f"{ctx.guild.name}({ctx.guild.id})",
                            value=f"이제부터 구매를 한 유저에게 <@&{mentioned_role_id}> 역할이 지급될거에요!", inline=False)

            await ctx.response.send_message(embed=embed, ephemeral=True)


@bot.slash_command(name='설정', description='서버 정보를 재설정합니다.')
async def Setting(interaction: nextcord.Interaction):
    if on_run:
        conn = sqlite3.connect(f'DB/server.db')
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS serverlist (serverid TEXT)")
        data = c.execute("SELECT * FROM serverlist WHERE serverid = ?", (interaction.guild.id,)).fetchone()
        conn.close()
        if data is None:
            embed = nextcord.Embed(title="⛔ㆍ사용불가", color=0xfffffe)
            embed.add_field(name=f"{interaction.guild.name}",
                            value=f"이 서버는 {SERVICE_NAME}에 가입되지 않았어요.\n`/등록` 명령어로 서비스에 가입해주세요.", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            conn = sqlite3.connect(f'SERVER/{interaction.guild.id}.db')
            c = conn.cursor()
            data = c.execute("SELECT * FROM serverinfo WHERE serverid = ?", (interaction.guild.id,)).fetchone()
            conn.close()
            if data is None:
                embed = nextcord.Embed(title="⛔ㆍ오류 발생", color=0xfffffe)
                embed.add_field(name="", value=f"오류가 발생했어요.", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)

            elif int(data[5]) in [role.id for role in interaction.user.roles]:
                embed = nextcord.Embed(title="🔄️ㆍ설정", color=0xfffffe)
                embed.add_field(name="", value=f"설정하시려면 아래의 버튼을 클릭해주세요.", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True, view=SetupButton())


# 이벤트 (접두사 커맨드)
@bot.event
async def on_message(message):
    global on_run
    if True:
        if message.author == bot.user:
            return

        # 라이센스 생성
        if message.content.startswith('.create '):
            def pick(_LENGTH):
                string_pool = string.ascii_letters + string.digits

                result = ""
                for i in range(_LENGTH):
                    result += random.choice(string_pool)

                return result

            if message.author.id in admin_ids:
                if not isinstance(message.channel, nextcord.channel.DMChannel):
                    try:
                        amount = int(message.content.split(" ")[1])
                    except:
                        await message.channel.send("올바른 생성 개수를 입력해주세요.")
                        return
                    if 1 <= amount <= 50:
                        codes = []
                        for _ in range(amount):
                            code = "cm-" + pick(10)
                            codes.append(code)
                            con = sqlite3.connect("DB/license.db")
                            c = con.cursor()
                            c.execute("CREATE TABLE IF NOT EXISTS licenses (license TEXT PRIMARY KEY)")
                            c.execute("INSERT INTO licenses (license) VALUES (?)", (code,))
                            con.commit()
                            con.close()
                            a = "\n".join(codes)
                            embed = nextcord.Embed(title=f"📄ㆍ라이센스", color=0xfffffe)
                            embed.add_field(name=f"라이센스가 생성되었어요.", value=f"```{a}```", inline=False)
                            await message.author.send(embed=embed)
                            await message.delete()

        # 라이센스 제거
        if message.content.startswith('.delete '):
            if message.author.id in admin_ids:
                if not isinstance(message.channel, nextcord.channel.DMChannel):
                    try:
                        license = message.content.split(" ")[1]
                    except:
                        await message.channel.send("올바른 형식의 라이센스를 입력해주세요.")
                        return
                    conn = sqlite3.connect('DB/license.db')
                    c = conn.cursor()
                    row = c.execute("SELECT * FROM licenses WHERE license=?", (license,)).fetchone()
                    if row is None:
                        conn.close()
                        await message.author.send(f"라이센스 `{license}`를 찾을 수 없어요.")
                        return
                    else:
                        c.execute("DELETE FROM licenses WHERE license=?", (license,))
                        conn.commit()
                        conn.close()
                        embed = nextcord.Embed(title=f"📄ㆍ라이센스", color=0xfffffe)
                        embed.add_field(name=f"라이센스를 삭제했어요.", value=f"```{license}```", inline=False)
                        await message.author.send(embed=embed)
                        await message.delete()

        # 라이센스 목록
        if message.content.startswith('.list'):
            if message.author.id in admin_ids:
                con = sqlite3.connect("DB/license.db")
                cur = con.cursor()
                cur.execute("SELECT license FROM licenses")
                results = cur.fetchall()
                a = [result[0] for result in results]
                con.close()
                file_content = io.StringIO()
                file_content.write(str(a))
                file_content.seek(0)
                discord_file = nextcord.File(file_content, filename="license.txt")
                await message.author.send(file=discord_file)
                file_content.close()
                await message.delete()

        # 서버 목록
        if message.content.startswith(".svlist"):
            if message.author.id in admin_ids:
                guild_list = bot.guilds
                for i in guild_list:
                    if message.author.guild_permissions.manage_guild:
                        text_channel = next((x for x in i.channels if type(x) is nextcord.channel.TextChannel), None)
                        if text_channel is not None:
                            invite = await text_channel.create_invite()
                            invite = invite.url
                        else:
                            invite = "채팅 채널 없음"
                    else:
                        invite = "권한없음"
                    embed = nextcord.Embed(title=f"{i.name} ({i.id})", color=0xfffffe)
                    if i.owner.avatar:
                        embed.set_author(name=i.owner.name, icon_url=i.owner.avatar.url)
                    else:
                        embed.set_author(name=i.owner.name,
                                         icon_url="https://archive.org/download/discordprofilepictures/discordblue.png")
                    embed.add_field(name="", value=invite, inline=False)
                    if i.icon:
                        embed.set_thumbnail(url=i.icon.url)
                    await message.author.send(embed=embed)

        # 서버 제거
        if message.content.startswith(".svdlt"):
            if message.author.id in admin_ids:
                guild_list = bot.guilds
                embed = nextcord.Embed(title=f"서버 제거를 하시려면 아래 버튼을 눌러주세요.", color=0xfffffe, )
                for i in guild_list:
                    embed.add_field(name=i.name, value=i.id, inline=False)
                await message.channel.send(embed=embed, view=ServerDel())

        # 백업
        if message.content.startswith("!backup"):
            if message.author.id in admin_ids:
                conn = sqlite3.connect(f'DB/server.db')
                cursor = conn.cursor()
                rows = cursor.execute("SELECT serverid FROM serverlist").fetchone()
                for row in rows:
                    print(row)
                    file = nextcord.File(f"SERVER/{row}.db", filename=f"{row}.db")
                    await message.author.send(file=file)
                conn.close()


# 호스팅 시 bot.run(TOKEN)
bot.run('')