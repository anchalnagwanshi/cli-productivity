import typer
from prodcli.LEARNING.problem_tracker import add_problem, list_problems, update_problem, open_problem_in_browser, get_problem_stats
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich import box

learning_app = typer.Typer()
console = Console()

@learning_app.command("add")
def add(
    url: str = typer.Option(..., "--url", "-u", help="Direct URL to the problem (e.g., LeetCode, GfG)."),
    name: str = typer.Option(..., "--name", "-n", help="Problem name/title (e.g., Two Sum, Kadane's Algorithm)."),
    platform: str = typer.Option(..., "--platform", "-p", help="Platform where the problem is found (e.g., LeetCode, GeeksforGeeks)."),
    difficulty: str = typer.Option("Unspecified", "--difficulty", "-d", help="Optional: Difficulty (e.g., Easy, Medium, Hard, Unspecified)."),
    status: str = typer.Option("Unsolved", "--status", "-s", help="Optional: Current status of the problem (e.g., Solved, Attempted, Revisit, Unsolved)."),
    notes: str = typer.Option("", "--notes", help="Optional: Any personal notes about the solution or concepts learned."),
    tags: str = typer.Option("", "--tags", "-t", help="Optional: Comma-separated tags/topics (e.g., Arrays, DP, Graph).")
):
    """Adds a new coding problem to track."""
    console.print("\n[bold blue]--- Problem Details to Add ---[/bold blue]")
    console.print(f"Platform: [green]{platform}[/green]")
    console.print(f"Name: [cyan]{name}[/cyan]")
    console.print(f"Difficulty: [purple]{difficulty}[/purple]")
    console.print(f"Status: [yellow]{status}[/yellow]")
    console.print(f"URL: [link={url}]{url}[/link]")
    console.print(f"Notes: [grey]{notes if notes else '[None]'}[/grey]")
    console.print(f"Tags: [magenta]{tags if tags else '[None]'}[/magenta]")

    if not typer.confirm("Does this look correct? Add problem?"):
        console.print("[red]Problem addition cancelled.[/red]")
        raise typer.Exit(code=0)

    add_problem(platform, url, name, difficulty, status, notes, tags)
    console.print(f"[bold green]Problem '{name}' ({platform}) added successfully![/bold green]")


@learning_app.command("list")
def list_problems_command(
    platform: str = typer.Option(None, "--platform", "-p", help="Filter by platform (e.g., LeetCode, GeeksforGeeks)"),
    status: str = typer.Option(None, "--status", "-s", help="Filter by status (e.g., Solved, Attempted, Unsolved)"),
    tag: str = typer.Option(None, "--tag", "-t", help="Filter by a specific tag (e.g., Arrays, DP)")
):
    """Lists your tracked coding problems."""
    problems = list_problems(platform=platform, status=status, tag=tag)
    if not problems:
        console.print("[yellow]No problems found matching your criteria.[/yellow]")
        return

    table = Table(
        title="[bold deep_sky_blue1]Your Coding Problems[/bold deep_sky_blue1]",
        show_header=True,
        header_style="bold green",
        box=box.ROUNDED,
        padding=(0, 1) 
    )

    # Define table columns
    table.add_column("#", justify="right", style="dim")
    table.add_column("Platform", justify="left", style="cyan")
    table.add_column("Name", justify="left", style="white", no_wrap=False)
    table.add_column("Difficulty", justify="left")
    table.add_column("Status", justify="left")
    table.add_column("Added Date", justify="left", style="dim")
    table.add_column("Last Modified", justify="left", style="dim")
    table.add_column("Tags", justify="left", style="magenta", no_wrap=False)
    table.add_column("URL", justify="left", style="blue underline")
    table.add_column("Notes", justify="left", style="grey50", no_wrap=False)


    for i, p in enumerate(problems):
        status_style: Style
        if p['status'] == 'Solved':
            status_style = Style(color="green", bold=True)
        elif p['status'] == 'Attempted':
            status_style = Style(color="bright_cyan", bold=True)
        elif p['status'] == 'Revisit':
            status_style = Style(color="bright_yellow", bold=True)
        elif p['status'] == 'Unsolved':
            status_style = Style(color="red", bold=True)
        else:
            status_style = Style(color="white") # Default

        difficulty_style: Style
        if p['difficulty'] == 'Easy':
            difficulty_style = Style(color="green")
        elif p['difficulty'] == 'Medium':
            difficulty_style = Style(color="yellow")
        elif p['difficulty'] == 'Hard':
            difficulty_style = Style(color="red")
        else:
            difficulty_style = Style(color="white") # Default

        added_date = p.get('added_date', 'N/A').split('T')[0] if p.get('added_date') else 'N/A'
        last_modified = p.get('last_modified_date', 'N/A').split('T')[0] if p.get('last_modified_date') else 'N/A'
        tags_str = ", ".join(p.get('tags', [])) if p.get('tags') else "N/A"
        
        notes_snippet = p.get('notes', 'N/A')
        if len(notes_snippet) > 50:
            notes_snippet = notes_snippet[:47] + "..."

        table.add_row(
            str(i + 1),
            p['platform'],
            Text(p['name'], style=Style(bold=True)), 
            Text(p['difficulty'], style=difficulty_style),
            Text(p['status'], style=status_style),
            added_date,
            last_modified,
            tags_str,
            f"[link={p['url']}]Link[/link]" if p.get('url') else "N/A",
            notes_snippet
        )

    console.print(table)
    console.print("[dim]Notes: Notes truncated for table display. Use 'open' command to view full URL and notes.[/dim]")


@learning_app.command("update")
def update_command(
    name: str = typer.Argument(..., help="Name of the problem to update"),
    new_status: str = typer.Option(None, "--status", "-s", help="New status (e.g., Solved, Attempted)"),
    new_notes: str = typer.Option(None, "--notes", "-n", help="New notes"),
    new_difficulty: str = typer.Option(None, "--difficulty", "-d", help="New difficulty"),
    new_tags: str = typer.Option(None, "--tags", "-t", help="New comma-separated tags (replaces existing tags)")
):
    """Updates details of an existing coding problem."""
    if update_problem(name, new_status, new_notes, new_difficulty, new_tags):
        console.print(f"[bold green]Problem '{name}' updated successfully.[/bold green]")
    else:
        console.print(f"[red]Problem '{name}' not found.[/red]")


@learning_app.command("open")
def open_command(name: str = typer.Argument(..., help="Name of the problem to open")):
    """Opens the URL of a tracked problem in your browser."""
    if not open_problem_in_browser(name):
        console.print(f"[red]Problem '{name}' not found or URL missing.[/red]")


@learning_app.command("stats")
def stats_command():
    """Shows statistics about your tracked coding problems."""
    stats = get_problem_stats()
    console.print(Panel("[bold blue]Coding Problem Statistics[/bold blue]", expand=False))
    console.print(f"Total problems tracked: [bold green]{stats['total_problems']}[/bold green]")
    
    console.print("\n[bold cyan]Problems by Platform:[/bold cyan]")
    for platform, count in stats['problems_by_platform'].items():
        console.print(f"  {platform}: {count}")
    
    console.print("\n[bold cyan]Problems by Status:[/bold cyan]")
    for status, count in stats['problems_by_status'].items():
        console.print(f"  {status}: {count}")
    
    console.print("\n[bold cyan]Problems by Difficulty:[/bold cyan]")
    for difficulty, count in stats['problems_by_difficulty'].items():
        console.print(f"  {difficulty}: {count}")