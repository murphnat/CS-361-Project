import urllib.request
import questionary
import platform
import requests
import zipfile
import random
import bcrypt
import typer
import json
import os


from email_validator import validate_email, EmailNotValidError
from password_validator import PasswordValidator
from rich.console import Console
from rich.console import Group
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from typing import List


# Typer Interface
console = Console()
app = typer.Typer()


def update_session_email(email):
    global session_email
    session_email = email


def clear_terminal():
    """
    Clears user terminal/CMD window.
    """

    # Get user OS.
    user_os = platform.system()

    # Use os-specific command.
    if user_os == 'Darwin':
        os.system('clear')
    else:
        os.system('cls')


def page_banner(banner: str):
    """
    Draws page panner on terminal/CMD window.
    """
    console.print(banner, justify="center")


def success_msg(panel_msg: str):
    """
    Draws successful panel message on terminal/CMD window.
    """
    panel = Panel(panel_msg, border_style="bold green")
    console.print(panel, justify="center")
    console.print()
    console.input(prompt="Press enter to continue...")


def failure_msg(panel_msg: str):
    """
    Draws failure panel message on terminal/CMD window.
    """
    panel = Panel(f"[blink]{panel_msg}[/blink]", border_style="bold red")
    console.print(panel, justify="center")
    console.print()
    console.input(prompt="Press enter to continue...")


def nav_bar(curr_pg):
    """
    Draws navigation bar panel on terminal/CMD window.
    """

    # List of all valid pages.
    page_list = ["Dashboard",
                 "Review",
                 "Search",
                 "Random",
                 "Help",
                 "Logout"]

    nav_text = Text()

    # Build rich text for nav bar.
    for i, pg in enumerate(page_list):

        # Highlight current page.
        color = "blue" if pg.lower() == curr_pg.lower() else "green"
        nav_text.append(pg, style=color)

        if i < len(page_list) - 1:
            nav_text.append(" | ")

    # Draw nav bar:
    panel = Panel(nav_text)
    console.print(panel, justify="center")
    console.print()


def navigate_to_page(prompt, curr_pg=None):
    """
    Allows for quick navigation
    between Kanji Crow's pages.
    """

    prompt = prompt.lower()

    if prompt == 'dashboard':
        dashboard()
    elif prompt == 'review':
        kanji_reviewer()
    elif prompt == 'search':
        kanji_search()
    elif prompt == 'random':
        kanji_wildcard_search()
    elif prompt == 'help':
        user_help()
    elif prompt == 'logout':
        console.print()
        console.print("Are you sure?", style="red")
        input = console.input(prompt="[Y/N]: ")

        if input in ["Yes", "yes", "Y", "y"]:
            update_session_email(None)
            welcome_menu()

        elif input in ["No", "no", "N", "n"]:
            navigate_to_page(curr_pg)

    failure_msg("Invalid Input")
    navigate_to_page(curr_pg)


def add_remove_kanji_to_db(kanji_obj, curr_page):
    """
    Adds/Removes kanji from a user's review queue / list of known kanji.
    """

    fp = "dummy_cache/user_dummy_data.json"
    with open(fp, 'r', encoding='utf-8') as kapi:
        ud = json.load(kapi)

    curr_user = session_email

    if kanji_obj in ud[curr_user]["kanji_data"]["known"]:
        failure_msg("This kanji is marked as known!")
        console.print()
        console.print("[red]Remove[/red] Kanji from known kanji list?")
        input = console.input(prompt="[Y/N]: ",)

        if input in ["Yes", "yes", "Y", "y"]:

            ud[curr_user]["kanji_data"]["known"].remove(kanji_obj)

            with open(fp, 'w', encoding='utf-8') as usdb:
                json.dump(ud, usdb, ensure_ascii=False, indent=4)

            removed_kanji = kanji_obj["kanji"]
            success_msg(f"{removed_kanji} Removed Successfully")

            console.print()

            console.print("Add Kanji to [green]Review Queue[/green]?")
            input = console.input(prompt="[Y/N]: ",)

            if input in ["Yes", "yes", "Y", "y"]:

                ud[curr_user]["kanji_data"]["reviews"].append(kanji_obj)

                with open(fp, 'w', encoding='utf-8') as usdb:
                    json.dump(ud, usdb, ensure_ascii=False, indent=4)

                added_kanji = kanji_obj["kanji"]
                success_msg(f"{added_kanji} Added Successfully")
                navigate_to_page(curr_page)

            elif input in ["No", "no", "N", "n"]:
                navigate_to_page(curr_page)

        elif input in ["No", "no", "N", "n"]:
            navigate_to_page(curr_page)

    if kanji_obj not in ud[curr_user]["kanji_data"]["reviews"]:

        console.print("Add Kanji to [green]Review Queue[/green]?")
        input = console.input(prompt="[Y/N]: ",)

        if input in ["Yes", "yes", "Y", "y"]:

            ud[curr_user]["kanji_data"]["reviews"].append(kanji_obj)

            with open(fp, 'w', encoding='utf-8') as usdb:
                json.dump(ud, usdb, ensure_ascii=False, indent=4)

            added_kanji = kanji_obj["kanji"]
            success_msg(f"{added_kanji} Added Successfully")
            navigate_to_page(curr_page)

        elif input in ["No", "no", "N", "n"]:
            navigate_to_page(curr_page)

    else:
        failure_msg("This kanji is already in your Review Queue!")
        console.print()
        console.print("[red]Remove[/red] Kanji from Review Queue?")
        input = console.input(prompt="[Y/N]: ",)

        if input in ["Yes", "yes", "Y", "y"]:

            ud[curr_user]["kanji_data"]["reviews"].remove(kanji_obj)

            with open(fp, 'w', encoding='utf-8') as usdb:
                json.dump(ud, usdb, ensure_ascii=False, indent=4)

            removed_kanji = kanji_obj["kanji"]
            success_msg(f"{removed_kanji} Removed Successfully")
            navigate_to_page(curr_page)

        elif input in ["No", "no", "N", "n"]:
            navigate_to_page(curr_page)


def gui(options: List[str], title: str = "Select an Option:") -> str:
    """
    Draws GUI with set of given options on
    terminal/CMD window using Questionary.
    """

    choice = questionary.select(
        title,
        choices=options,
        use_indicator=True,
        use_shortcuts=True,
        instruction=" ",
        ).ask()

    return choice


def download_kapi_data(curr_page: str):
    """
    Downloads and unzips a copy of the
    KanjiAPI for use with search features.

    SRC: https://kanjiapi.dev/#!/
    """

    console.print()
    failure_msg("This feature requires a local copy of the Kanji API.")
    console.print()

    options = [
        "Yes",
        "No"]
    choice = gui(options, "Download?")

    # Download API cache:
    if choice == 'Yes':

        dir = os.path.dirname("kanjiapi_full.zip")
        if dir and not os.path.exists(dir):
            os.makedirs(dir)
        url = 'https://kanjiapi.dev/kanjiapi_full.zip'
        urllib.request.urlretrieve(url, "kanjiapi_full.zip")

        with zipfile.ZipFile("kanjiapi_full.zip", 'r') as zf:
            zf.extractall("kanjiapi_cache")

        os.remove("kanjiapi_full.zip")

        navigate_to_page(curr_page)

    elif choice == 'No':
        navigate_to_page(curr_page)



@app.command()
def welcome_menu():
    """
    Kanji Crow Welcome Menu. Allows users to
    login, register, or exit from the service.
    """

    # Kanji Crow's ASCII Logo.
    kc_logo = """[bold blue]
    ██╗  ██╗ █████╗ ███╗   ██╗     ██╗██╗     ██████╗██████╗  ██████╗ ██╗    ██╗
    ██║ ██╔╝██╔══██╗████╗  ██║     ██║██║    ██╔════╝██╔══██╗██╔═══██╗██║    ██║
    █████╔╝ ███████║██╔██╗ ██║     ██║██║    ██║     ██████╔╝██║   ██║██║ █╗ ██║
    ██╔═██╗ ██╔══██║██║╚██╗██║██   ██║██║    ██║     ██╔══██╗██║   ██║██║███╗██║
    ██║  ██╗██║  ██║██║ ╚████║╚█████╔╝██║    ╚██████╗██║  ██║╚██████╔╝╚███╔███╔╝
    ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚════╝ ╚═╝     ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚══╝╚══╝
    [/bold blue]"""

    # Draw banner.
    clear_terminal()
    page_banner(kc_logo)

    # Draw Kanji Crow's tagline text blurb.
    tag_text = Text("Master Japanese Kanji - Search, view, and study 13k "
                    "characters to strengthen your Japanese skills.",
                    style="light blue")
    console.print(tag_text, justify="center")
    console.print()

    # Draw navigation options.
    options = [
        "Login",
        "Register",
        "-> Exit"]
    choice = gui(options)

    # Call Login.
    if choice == options[0]:
        login_user()

    # Call Registration.
    elif choice == options[1]:
        register_user()

    # Terminate Program.
    elif choice == options[2]:
        console.print()
        console.print("Are you sure?", style="red")
        input = console.input(prompt="[Y/N]: ")

        # Exit and clear terminal.
        if input in ["Yes", "yes", "Y", "y"]:
            clear_terminal()
            raise typer.Exit()

        # Redirect to Welcome Menu.
        elif input in ["No", "no", "N", "n"]:
            welcome_menu()

        else:

            # Draw error message.
            failure_msg("Invalid Input")
            welcome_menu()


@app.command()
def register_user():
    """
    Allows users to register for Kanji Crow.
    Requires a valid email and password.
    """

    clear_terminal()
    page_banner("""[bold green]
    ██████╗ ███████╗ ██████╗ ██╗███████╗████████╗███████╗██████╗
    ██╔══██╗██╔════╝██╔════╝ ██║██╔════╝╚══██╔══╝██╔════╝██╔══██╗
    ██████╔╝█████╗  ██║  ███╗██║███████╗   ██║   █████╗  ██████╔╝
    ██╔══██╗██╔══╝  ██║   ██║██║╚════██║   ██║   ██╔══╝  ██╔══██╗
    ██║  ██║███████╗╚██████╔╝██║███████║   ██║   ███████╗██║  ██║
    ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝
    [/bold green]""")

    def validate_user_email(user_email):
        """
        Validates a user's email.
        Ensures prefix, @, provider, ., and suffix.
        """
        try:
            emailinfo = validate_email(user_email, check_deliverability=False)
            normalized_email = emailinfo.normalized  # Recommended in docs.
            return True
        except EmailNotValidError as e:
            return (str(e))

    email = questionary.text(
        "Email: ",
        validate=validate_user_email
    ).ask()

    # Validator Schema & Ruleset:
    pws = PasswordValidator()
    pws.min(8)
    pws.max(16)
    pws.has().uppercase()
    pws.has().digits()
    pws.has().no().spaces()

    def validate_user_password(user_password):
        """
        Validates a user's password.
        Ensures length b/t 8 and 16,
        1 upper, 1 digit, no spaces.
        """

        # Check min length.
        temp = PasswordValidator().min(8)
        if not temp.validate(user_password):
            return "Too short! Must be >= 8."

        # Check max length.
        temp = PasswordValidator().max(16)
        if not temp.validate(user_password):
            return "Too long! Must be <= 16."

        # Check uppercase char.
        temp = PasswordValidator().has().uppercase()
        if not temp.validate(user_password):
            return "Missing at least 1 uppercase char."

        # Check digit.
        temp = PasswordValidator().has().digits()
        if not temp.validate(user_password):
            return "Missing at least 1 digit."

        # Check no spaces.
        temp = PasswordValidator().has().no().spaces()
        if not temp.validate(user_password):
            return "Cannot contain spaces."

        return pws.validate(user_password)

    password = questionary.password(
        "Password: ",
        validate=validate_user_password
    ).ask()

    def verify_user_password(user_password):
        """
        Compares user's first and second password entry.
        Returns valid if both entries are identical.
        """

        # Check for mismatched passwords.
        if user_password != password:
            return "Passwords are not identical."
        else:
            return True

    verify_password = questionary.password(
        "Verify: ",
        validate=verify_user_password
    ).ask()

    # Hash user password with bcrypt.
    def hash_user_pw(password):
        """
        Salts and hashes user password using bcrypt.
        """

        # Encode pw.
        if isinstance(password, str):
            password = password.encode('utf-8')

        # Salt and return modified pw.
        salt = bcrypt.gensalt(10)
        hashed_pw = bcrypt.hashpw(password, salt)

        return hashed_pw.decode('utf-8')

    if password == verify_password:

        # Init file path & dict.
        fp = "dummy_cache/user_dummy_data.json"
        usdb = {}

        # Open user database:
        if os.path.exists(fp) and os.path.getsize(fp) > 0:
            with open(fp, "r", encoding="utf-8") as file:
                usdb = json.load(file)

        # Duplicate email -> error:
        if email in usdb:
            failure_msg("Email already registered. Try another.")

            # Restart registration process.
            register_user()

        # Valid email -> register user:
        else:

            # Store (hashed) user data.
            pw = hash_user_pw(password)

            if os.path.exists(fp) and os.path.getsize(fp) > 0:
                with open(fp, "r", encoding="utf-8") as file:
                    usdb = json.load(file)

            usdb[email] = {
                "password": pw,
                "kanji_data": {
                    "reviews": [],
                    "known": []
                }
            }

            with open(fp, "w", encoding="utf-8") as file:
                json.dump(usdb, file, indent=4)

            # Display success and return to welcome.
            success_msg("Registered Successfully")
            welcome_menu()

    # TODO:
    # Handle user data as microservice.


def login_user():
    """
    Allows users to login with their credentials.
    Successful logins redirect to the dashboard.
    """

    clear_terminal()
    page_banner("""[bold green]
    ██╗      ██████╗  ██████╗ ██╗███╗   ██╗
    ██║     ██╔═══██╗██╔════╝ ██║████╗  ██║
    ██║     ██║   ██║██║  ███╗██║██╔██╗ ██║
    ██║     ██║   ██║██║   ██║██║██║╚██╗██║
    ███████╗╚██████╔╝╚██████╔╝██║██║ ╚████║
    ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝╚═╝  ╚═══╝
    [/bold green]""")

    email = questionary.text(
        "Email: ",
    ).ask()

    pw = questionary.password(
        "Password: ",
    ).ask()

    ud = []
    ud.append(email)
    ud.append(pw)

    # Init file path & dict.
    fp = "dummy_cache/user_dummy_data.json"
    usdb = {}

    # Open user database:
    if os.path.exists(fp) and os.path.getsize(fp) > 0:
        with open(fp, "r", encoding="utf-8") as file:
            usdb = json.load(file)

    if email not in usdb:
        failure_msg("No account found with this email. Please register.")
        welcome_menu()

    else:

        hpw = usdb[email]['password']

        if bcrypt.checkpw(pw.encode('utf-8'), hpw.encode('utf-8')):

            success_msg("Login Successful")

            update_session_email(email)
            dashboard()

        else:
            failure_msg("Incorrect Password. Try again.")

            welcome_menu()

    # TODO:
    # Handle user data as Microservice.


def dashboard():
    """
    Permits user navigation to various pages.
    Provides kanji statistics overview to user.
    """

    clear_terminal()
    page_banner("""[bold blue]
    ██████╗  █████╗ ███████╗██╗  ██╗██████╗  ██████╗  █████╗ ██████╗ ██████╗
    ██╔══██╗██╔══██╗██╔════╝██║  ██║██╔══██╗██╔═══██╗██╔══██╗██╔══██╗██╔══██╗
    ██║  ██║███████║███████╗███████║██████╔╝██║   ██║███████║██████╔╝██║  ██║
    ██║  ██║██╔══██║╚════██║██╔══██║██╔══██╗██║   ██║██╔══██║██╔══██╗██║  ██║
    ██████╔╝██║  ██║███████║██║  ██║██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝
    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝
    [/bold blue]""")

    nav_bar("Dashboard")

    fp = "dummy_cache/user_dummy_data.json"
    with open(fp, 'r', encoding='utf-8') as usdb:
        ud = json.load(usdb)

    # Get user specific data.
    curr_user = session_email
    known_kanji = len(ud[curr_user]["kanji_data"]["known"])
    kanji_count = "Known: " + str(known_kanji) + " / " + "13108"

    stat_panel = Panel(
        kanji_count,
        title="Kanji Stats",
        border_style="bright_blue"
    )

    console.print(Align.center(stat_panel))
    console.print()

    pg = questionary.text("Input: ").ask()
    navigate_to_page(pg, "dashboard")

    # TODO:
    # Handle dashboard stats as Microservice
    # ADD: RECENTLY LEARNED KANJI


def kanji_reviewer():
    """
    Enables users to review kanji in their
    review queue in a flashcard format.
    """

    clear_terminal()
    pg_banner = ("""[bold blue]
    ██████╗ ███████╗██╗   ██╗██╗███████╗██╗    ██╗
    ██╔══██╗██╔════╝██║   ██║██║██╔════╝██║    ██║
    ██████╔╝█████╗  ██║   ██║██║█████╗  ██║ █╗ ██║
    ██╔══██╗██╔══╝  ╚██╗ ██╔╝██║██╔══╝  ██║███╗██║
    ██║  ██║███████╗ ╚████╔╝ ██║███████╗╚███╔███╔╝
    ╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚═╝╚══════╝ ╚══╝╚══╝
    [/bold blue]""")
    page_banner(pg_banner)

    nav_bar("Review")

    fp = "dummy_cache/user_dummy_data.json"
    with open(fp, 'r', encoding='utf-8') as usdb:
        ud = json.load(usdb)

    # Get user specific data.
    curr_user = session_email
    user_reviews = ud[curr_user]["kanji_data"]["reviews"]

    if len(user_reviews) > 0:
        ck = random.choice(user_reviews)
    else:
        failure_msg("No kanji in review queue!")
        navigate_to_page("Dashboard")

    kanji_char = Text(ck["kanji"], style="bold magenta", justify="center")

    # Kanji Card (Front):
    front_panel = Panel(
        kanji_char,
        width=20,
        padding=(2, 5),
        title="Front",
        border_style="bright_blue"
    )

    # Review Queue:
    rem_str = str(len(ud[curr_user]["kanji_data"]["reviews"]))
    rem_reviews = Text(rem_str, style="bold magenta", justify="center")

    review_queue = Panel(
        rem_reviews,
        title="Review Count",
        border_style="bright_blue"
    )

    console.print(Align.center(front_panel))
    console.print(Align.center(review_queue))

    console.input(prompt="Press enter to flip card!")

    clear_terminal()
    page_banner(pg_banner)
    nav_bar("Review")

    kanji_info = Table(show_header=False, padding=(0, 2), box=None)
    kanji_info.add_row("JLPT Level:", f"{ck['jlpt']}")

    meanings = ", ".join(ck["meanings"])
    kanji_info.add_row("Keyword:", ck["heisig_en"])
    kanji_info.add_row("Meanings:", meanings)

    kun = ck["kun_readings"][0] if ck["kun_readings"] else "N/A"
    on = ck["on_readings"][0] if ck["on_readings"] else "N/A"
    kanji_info.add_row("On Reading", on)
    kanji_info.add_row("Kun Reading", kun)

    card_group = Group(
        kanji_char,
        "",
        kanji_info
    )

    back_panel = Panel(
        card_group,
        width=40,
        padding=(1, 2),
        title=(f"Back: - Kanji Info: {ck['kanji']}"),
        border_style="bright_blue",
    )

    console.print(Align.center(back_panel))
    console.print(Align.center(review_queue))

    options = [
        "Good (Known)",
        "Hard (Again)",
        "-> Dashboard"]
    choice = gui(options, "Rate Review:")

    if choice == options[0]:
        ud[curr_user]["kanji_data"]["known"].append(ck)
        user_reviews.remove(ck)
        success_msg(f"{ck['kanji']} removed from Review Queue")

        with open(fp, 'w', encoding='utf-8') as usdb:
            json.dump(ud, usdb, ensure_ascii=False, indent=4)

        navigate_to_page("Review")

    elif choice == options[1]:
        navigate_to_page("Review")

    else:
        navigate_to_page("Dashboard")


def kanji_search():
    """
    Allows users to search for kanji directly using
    the KanjiAPI or to search in English using a locally
    cached download of the KanjiAPI.

    Users can add or remove direct kanji lookup results
    to their review queue from the search page.
    """

    clear_terminal()
    pg_banner = """[bold blue]
    ███████╗███████╗ █████╗ ██████╗  ██████╗██╗  ██╗
    ██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝██║  ██║
    ███████╗█████╗  ███████║██████╔╝██║     ███████║
    ╚════██║██╔══╝  ██╔══██║██╔══██╗██║     ██╔══██║
    ███████║███████╗██║  ██║██║  ██║╚██████╗██║  ██║
    ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
    [/bold blue]"""
    page_banner(pg_banner)

    nav_bar("Search")

    options = [
        "Kanji Lookup",
        "English to Kanji",
        "-> Dashboard"]
    choice = gui(options)

    # Kanji Lookup.
    if choice == options[0]:

        # Get kanji input.
        kq = questionary.text("Input: ").ask()

        # Check if valid query.
        if not kq.strip():
            failure_msg("Empty query. Try again.")
            navigate_to_page("Search")

        else:

            base_url = "https://kanjiapi.dev/v1"
            url = f"{base_url}/kanji/{kq}"
            response = requests.get(url)

            if response.status_code != 200:
                failure_msg("No Result / API Error.")

            else:

                res = response.json()

                # Handle JSON edge case issues:
                kun = res["kun_readings"][0] if res["kun_readings"] else "N/A"
                on = res["on_readings"][0] if res["on_readings"] else "N/A"

                # Build kanji search results table:
                kanji_table = Table("Kanji", "Meaning", "JLPT", "Kun", "On")
                kanji_table.add_row(res["kanji"], res["heisig_en"],
                                    str(res["jlpt"]), kun, on)

                # Render Table:
                console.print(kanji_table, justify="center")
                console.print()

                # Prompt to add to db:
                add_remove_kanji_to_db(res, "search")

    # English -> Kanji
    elif choice == options[1]:

        fp = 'dummy_cache/kanji_dummy_data.json'
        with open(fp, 'r', encoding='utf-8') as kapi:
            kanji_data = json.load(kapi)

        # Create Kanji API dictionary.
        kd = kanji_data.get("kanjis", {})

        # Get user kanji query:
        msg = "Input (Type 'quit' to END): "
        kq = questionary.text(msg).ask().lstrip().strip().lower()

        while True:

            if not kq.strip():
                failure_msg("Empty query. Try again.")
                navigate_to_page("search")
                break

            # Terminate search commands:
            if kq in ['Quit', 'quit', 'Q', 'q',]:
                navigate_to_page("search")
                break

            # Init match list.
            matching_kanji = []

            # Parse kd for matching kanji.
            for kanji, entry in kd.items():

                # Get English 'Heisig' Keyword.
                heisig_en = entry.get("heisig_en")

                # Check if not NULL and matches user kq:
                if heisig_en and kq in heisig_en.lower():
                    res = {
                        'kanji': kanji,
                        'heisig_en': heisig_en
                    }

                    # Update match list.
                    matching_kanji.append(res)

            # No matching kanji:
            if not matching_kanji:
                failure_msg("No matching kanji")
                navigate_to_page("search")
                break

            else:

                # Result vars:
                curr_res = 0
                res_count = 3
                tot_res = len(matching_kanji)

                while curr_res < tot_res:

                    # Re-render page:
                    clear_terminal()
                    page_banner(pg_banner)
                    nav_bar('search')

                    # Limit results to 3 kanji per 'page.'
                    end_res = min(curr_res + res_count, tot_res)
                    for i in range(curr_res, end_res):
                        kanji = matching_kanji[i]
                        kanji_table = Table("Kanji", "Meaning")
                        kanji_table.add_row(kanji['kanji'], kanji['heisig_en'])
                        console.print(kanji_table, justify="center")

                    curr_res += res_count

                    if curr_res < tot_res:
                        options = [
                            "Yes",
                            "No"]
                        choice = gui(options, "Show more?")

                        if choice == options[1]:
                            navigate_to_page("search")
                            break

                    else:
                        console.print()
                        failure_msg("End of results")
                        navigate_to_page("search")
                        break

    elif choice == options[2]:
        navigate_to_page("dashboard")

    # TODO:
    # Handle API and local search (maybe?) as Microservice.
    # Filter by JLPT
    # Filter by grade
    # Copy result to clipboard?

    navigate_to_page("search")  # Redundant


def kanji_wildcard_search():
    """
    Allows users to generate a random kanji
    from a locally cached version of the KanjiAPI.
    """

    clear_terminal()
    page_banner("""[bold blue]
    ██████╗  █████╗ ███╗   ██╗██████╗  ██████╗ ███╗   ███╗
    ██╔══██╗██╔══██╗████╗  ██║██╔══██╗██╔═══██╗████╗ ████║
    ██████╔╝███████║██╔██╗ ██║██║  ██║██║   ██║██╔████╔██║
    ██╔══██╗██╔══██║██║╚██╗██║██║  ██║██║   ██║██║╚██╔╝██║
    ██║  ██║██║  ██║██║ ╚████║██████╔╝╚██████╔╝██║ ╚═╝ ██║
    ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝ ╚═╝     ╚═╝
    [/bold blue]""")

    nav_bar("Random")

    options = [
        "Generate Random Kanji", "-> Dashboard"]
    choice = gui(options)

    # Kanji Lookup.
    if choice == options[0]:

        fp = 'dummy_cache/kanji_dummy_data.json'
        with open(fp, 'r', encoding='utf-8') as kapi:
            kanji_data = json.load(kapi)

        keys = list(kanji_data["kanjis"].keys())

        while True:

            random_key = keys[random.randint(0, len(keys)-1)]
            rk = kanji_data['kanjis'][random_key]

            if rk.get('heisig_en'):
                break

        console.print()

        kun = rk["kun_readings"][0] if rk["kun_readings"] else "N/A"
        on = rk["on_readings"][0] if rk["on_readings"] else "N/A"

        kanji_table = Table("Kanji", "Meaning", "JLPT", "Kun", "On")
        kanji_table.add_row(rk["kanji"], rk["heisig_en"],
                            str(rk["jlpt"]), kun, on)

        console.print(kanji_table, justify="center")
        console.print()
        add_remove_kanji_to_db(rk, "random")

    elif choice == options[1]:
        navigate_to_page('dashboard')

    # TODO for later:
    # Handle wildcard search as Microservice
    # Filter by JLPT
    # Filter by grade
    # Copy first result to clipboard?


def user_help():
    """
    Allows users to explore a brief
    overview of the features of Kanji Crow.
    """

    clear_terminal()
    page_banner("""[bold green]
        ██╗  ██╗███████╗██╗     ██████╗
        ██║  ██║██╔════╝██║     ██╔══██╗
        ███████║█████╗  ██║     ██████╔╝
        ██╔══██║██╔══╝  ██║     ██╔═══╝
    ██║  ██║███████╗███████╗██║
    ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝
    [bold green]""")

    nav_bar("Help")

    # Help Sections:
    options = [
        "Review",
        "Search",
        "Random",
        "-> Dashboard"]
    choice = gui(options, "Select a feature to learn about:")

    if choice == options[0]:
        console.print()
        console.print("[bold magenta]Select 'Review' to access " \
                      "your Kanji review queue. Reviews are presented "
                      "in flashcard format. Flip the card to see " \
                      "additional details - e.g. pronunciation, " \
                      "English meaning, JLPT ranking, and status. " \
                      "Card status can be updated by selecting either "
                      "'learning' or 'known.' Marking a card 'Known' " \
                      "automatically removes it from your " \
                      "review queue.[/bold magenta]")
        console.print()
        console.input(prompt="Press enter to continue...")
        navigate_to_page("help")

    if choice == options[1]:
        console.print()
        console.print("[bold magenta]Select 'Search' to find specific " \
                      "kanji of interest. 'Kanji Lookup' allows users " \
                      "to directly search-up a kanji. Users can add or "\
                      "remove direct lookup results to or from their" \
                      " review queue. 'English -> Kanji' search allows users" \
                      " to search for kanji using an english keyword." \
                      "[/bold magenta]")

        console.print()
        console.input(prompt="Press enter to continue...")
        navigate_to_page("help")

    if choice == options[2]:
        console.print()
        console.print("[bold magenta]Select 'Random' to be served " \
                      "a random kanji. Random kanji results can be " \
                      "added or removed to or from a user's review queue." \
                      "[/bold magenta]")
        console.print()
        console.input(prompt="Press enter to continue...")
        navigate_to_page("help")

    if choice == options[3]:
        navigate_to_page("dashboard")


@app.callback(invoke_without_command=True)
def main():
    welcome_menu()


if __name__ == '__main__':

    # Clear terminal.
    clear_terminal()

    # Init Typer.
    app()
