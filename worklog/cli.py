import argparse
from pathlib import Path

from worklog import config, store
from worklog.core import upsert
from worklog.dates import today_str, format_hours, parse_hours
from worklog.project import resolve_project, init_project
from worklog.sheets import open_worksheet


def _resolve(args_project, cfg):
    if args_project:
        return args_project
    name, _ = resolve_project(Path.cwd(), cfg)
    return name


def _get_backend(backend, backend_factory, cfg):
    if backend is not None:
        return backend
    factory = backend_factory or open_worksheet
    return factory(cfg)


def cmd_add(args, cfg, backend, backend_factory):
    project = _resolve(args.project, cfg)
    if not project:
        print('No project resolved. Run `worklog init "<Project>"` or pass --project.')
        return 1
    date = args.date or today_str()
    hours = parse_hours(args.hours)
    entry = {"date": date, "hours": hours, "text": args.text, "project": project}

    if args.dry_run:
        print(f"[dry-run] {date} | {format_hours(hours)} | {args.text} | {project}")
        return 0

    try:
        b = _get_backend(backend, backend_factory, cfg)
    except Exception as exc:  # offline / no creds — never lose data
        store.buffer_entry(entry)
        print(f"Could not reach Google Sheets ({exc}); entry buffered for later flush.")
        return 0

    action, _ = upsert(b, date, hours, args.text, project)
    print(f"{action}: {date} | {format_hours(hours)} | {args.text} | {project}")
    return 0


def cmd_flush(args, cfg, backend, backend_factory):
    pending = store.read_pending()
    if not pending:
        print("Nothing to flush.")
        return 0
    try:
        b = _get_backend(backend, backend_factory, cfg)
    except Exception as exc:
        print(f"Still cannot reach Google Sheets ({exc}); kept {len(pending)} buffered.")
        return 1
    for e in pending:
        upsert(b, e["date"], parse_hours(e["hours"]), e["text"], e["project"])
    store.clear_pending()
    print(f"Flushed {len(pending)} entr{'y' if len(pending) == 1 else 'ies'}.")
    return 0


def cmd_show(args, cfg, backend, backend_factory):
    date = args.date or today_str()
    try:
        b = _get_backend(backend, backend_factory, cfg)
    except Exception as exc:
        print(f"Could not reach Google Sheets ({exc}).")
        return 1
    for row in b.get_all_values()[1:]:
        if row and row[0] == date:
            print(" | ".join(str(c) for c in row))
    return 0


def cmd_projects(args, cfg, backend, backend_factory):
    for p in cfg.get("known_projects", []):
        print(p)
    return 0


def cmd_init(args, cfg, backend, backend_factory):
    init_project(Path.cwd(), args.name, cfg)
    print(f'Initialized worklog tracking for "{args.name}" in {Path.cwd()}')
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="worklog")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--dry-run", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)

    pa = sub.add_parser("add", parents=[common])
    pa.add_argument("--project")
    pa.add_argument("--hours", required=True)
    pa.add_argument("--text", required=True)
    pa.add_argument("--date")
    pa.set_defaults(func=cmd_add)

    pi = sub.add_parser("init", parents=[common])
    pi.add_argument("name")
    pi.set_defaults(func=cmd_init)

    ps = sub.add_parser("show", parents=[common])
    ps.add_argument("--date")
    ps.set_defaults(func=cmd_show)

    sub.add_parser("projects", parents=[common]).set_defaults(func=cmd_projects)
    sub.add_parser("flush", parents=[common]).set_defaults(func=cmd_flush)
    return p


def main(argv=None, backend=None, backend_factory=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = config.load_config()
    return args.func(args, cfg, backend, backend_factory)


if __name__ == "__main__":
    import sys

    sys.exit(main())
