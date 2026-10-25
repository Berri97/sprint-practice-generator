"""Sprint draw training. Python 3.10+. CLI: python sprint_practice_generator.py
UI: streamlit run sprint_practice_generator.py
ISU Sports Rules effective 12 June 2026, Rules 240.4.2 and 244.7.
Only completed, valid races; no withdrawals, DNS, DNF, DQ or qualification limits.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import random
import secrets
from pathlib import Path

FICTIONAL_WOMEN_NAMES = [
    "Lina van Aken",
    "Noor El Amrani",
    "Sofia Petrovic",
    "Aya Nakamori",
    "Mila de Wit",
    "Fatima Rahmani",
    "Yara Mensah",
    "Elin Söderberg",
    "Amara Okafor",
    "Lotte Vermeer",
    "Inès Dubois",
    "Sara Jansen",
    "Nadia Kowalska",
    "Mei-Ling Chen",
    "Eva Lindström",
    "Rania Haddad",
    "Zoë van Dalen",
    "Leila Benali",
    "Nora Andersen",
    "Iris Hoekstra",
    "Samira Diallo",
    "Marta Nowak",
    "Hana Kovač",
    "Aisha Williams",
    "Liv de Graaf",
    "Camila Ribeiro",
    "Anika Sharma",
    "Eleni Papadopoulos",
    "Mariam Tesfaye",
    "Julie Martens",
    "Sanne Kuiper",
    "Alina Popescu",
    "Nour Abdi",
    "Chiara Rossi",
    "Lucía Moreno",
    "Daria Ivanova",
    "Maëlle Laurent",
    "Amina Yusuf",
    "Keira O'Connell",
    "Tess van Loon",
]

FICTIONAL_MEN_NAMES = [
    "Luca van Aken",
    "Omar El Amrani",
    "Milan Petrovic",
    "Haruto Nakamori",
    "Daan de Wit",
    "Yassin Rahmani",
    "Kwame Mensah",
    "Erik Söderberg",
    "Chidi Okafor",
    "Jasper Vermeer",
    "Mathis Dubois",
    "Sam Jansen",
    "Jakub Kowalski",
    "Wei Chen",
    "Nils Lindström",
    "Karim Haddad",
    "Finn van Dalen",
    "Adam Benali",
    "Mikkel Andersen",
    "Thijs Hoekstra",
    "Moussa Diallo",
    "Piotr Nowak",
    "Ivan Kovač",
    "Malik Williams",
    "Bram de Graaf",
    "Gabriel Ribeiro",
    "Arjun Sharma",
    "Nikos Papadopoulos",
    "Dawit Tesfaye",
    "Julien Martens",
    "Sven Kuiper",
    "Andrei Popescu",
    "Idris Abdi",
    "Marco Rossi",
    "Diego Moreno",
    "Dmitri Ivanov",
    "Louis Laurent",
    "Khalid Yusuf",
    "Sean O'Connell",
    "Timo van Loon",
]

RACES = ['500_1', '1000_1', '500_2', '1000_2']
LABELS = {'500_1': 'First 500 m', '1000_1': 'First 1000 m',
          '500_2': 'Second 500 m', '1000_2': 'Second 1000 m'}
RULE_URL = 'https://www.isu.org/speed-skating-rules'


def distance(race):
    return int(race.split('_')[0])


def time_text(cs):
    minutes, rest = divmod(cs, 6000)
    seconds, hundredths = divmod(rest, 100)
    return f'{minutes}:{seconds:02d}.{hundredths:02d}' if minutes else f'{seconds}.{hundredths:02d}'


def score_units(skater, count):
    """Integer units of 0.005 points; avoid floating-point tie errors."""
    return sum(skater['times'][r] * (2 if distance(r) == 500 else 1)
               for r in RACES[:count])


def draw_key(skater, target):
    count = 2 if target == '500_2' else 3
    first = target.replace('_2', '_1')
    return score_units(skater, count), skater['times'][first]


def starting_pairs(skaters, target):
    """Best from each required lane meet; best pair last. Solos keep their lane.
    An unresolved points + first-race-time tie is rejected instead of using bibs.
    """
    if target not in ('500_2', '1000_2'):
        raise ValueError('Target must be 500_2 or 1000_2.')
    first = target.replace('_2', '_1')
    keys = [draw_key(s, target) for s in skaters]
    if len(keys) != len(set(keys)):
        raise ValueError('Unresolved draw tie: equal points AND equal first-race time. '
                         'This version requires a case without this situation.')
    ranked = sorted(skaters, key=lambda s: draw_key(s, target))
    new_inner = [s for s in ranked if s['lanes'][first] == 'O']
    new_outer = [s for s in ranked if s['lanes'][first] == 'I']
    best_first = [(new_inner[i]['bib'] if i < len(new_inner) else None,
                   new_outer[i]['bib'] if i < len(new_outer) else None)
                  for i in range(max(len(new_inner), len(new_outer)))]
    return list(reversed(best_first))


def generate_case(gender='men', n=24, seed=1, target='500_2', level='senior', tie=False):
    if gender not in ('men', 'women') or not 4 <= n <= 40:
        raise ValueError('Choose men/women and 4–40 skaters.')
    if target not in ('500_2', '1000_2') or level not in ('senior', 'junior'):
        raise ValueError('Invalid exercise or performance level.')
    rng = random.Random(seed)
    names = FICTIONAL_MEN_NAMES if gender == 'men' else FICTIONAL_WOMEN_NAMES
    skaters = []
    base = (35.4, 70.8) if gender == 'men' else (39.0, 78.4)
    for i, name in enumerate(rng.sample(names, n)):
        ability = rng.uniform(0, 3.3)
        profile = rng.uniform(-0.65, 0.65)
        extra = 1.4 if level == 'junior' else 0
        t500 = base[0] + ability + profile + extra
        t1000 = base[1] + ability * 2.25 - profile * 1.25 + extra * 2.4
        times = {}
        for race in RACES:
            center = t500 if distance(race) == 500 else t1000
            noise = 0.13 if distance(race) == 500 else 0.32
            times[race] = round((center + rng.gauss(0, noise)) * 100)
        skaters.append(dict(bib=51+i, name=name, times=times, lanes={}))
    # Already drawn first-day lanes: balanced, independent on each distance.
    # Odd field: one extra I (the first-day solo starts in I).
    for race in RACES[:2]:
        order = list(skaters)
        rng.shuffle(order)
        for i, s in enumerate(order):
            s['lanes'][race] = 'I' if i % 2 == 0 else 'O'
    if tie:
        # Two nearby performances, equal points, distinct first-race times.
        a, b = sorted(skaters, key=lambda s: s['times']['500_1'])[1:3]
        for race in RACES[:3]:
            b['times'][race] = a['times'][race]
        b['times']['500_1'] += 10
        b['times']['1000_1'] -= 20
        # A draw tie only changes the pairing if both skaters belong to the
        # same lane group. Swap with a third skater to keep day-one lanes
        # balanced, including for odd fields.
        first_race = target.replace('_2', '_1')
        if b['lanes'][first_race] != a['lanes'][first_race]:
            other = next(s for s in skaters
                         if s is not a and s is not b
                         and s['lanes'][first_race] == a['lanes'][first_race])
            b['lanes'][first_race], other['lanes'][first_race] = (
                other['lanes'][first_race], b['lanes'][first_race])
    # Extremely rare complete ties are regenerated deterministically, never bib-sorted.
    for attempt in range(100):
        try:
            for target_race in ('500_2', '1000_2'):
                pairs = starting_pairs(skaters, target_race)
                by_bib = {s['bib']: s for s in skaters}
                for inner, outer in pairs:
                    if inner is not None:
                        by_bib[inner]['lanes'][target_race] = 'I'
                    if outer is not None:
                        by_bib[outer]['lanes'][target_race] = 'O'
            break
        except ValueError:
            # Preserve any deliberately forced points tie; change the first race
            # only for non-target exact ties, then recompute the draw.
            for s in skaters:
                s['times']['1000_1'] += rng.randrange(1, 5)
    else:
        raise ValueError('Could not create a case without an unresolved tie.')
    if tie:
        count = 2 if target == '500_2' else 3
        if score_units(a, count) != score_units(b, count):
            raise ValueError('Could not preserve the requested points tie; choose another seed.')
    return dict(version=1, gender=gender, n=n, seed=seed, target=target,
                level=level, tie=tie, skaters=skaters)


def classification(case, count):
    target = '500_2' if count == 2 else '1000_2'
    ranked = sorted(case['skaters'], key=lambda s: draw_key(s, target))
    rows = []
    previous, rank = None, 0
    for i, s in enumerate(ranked, 1):
        points = score_units(s, count)
        if points != previous:
            rank = i
        previous = points
        row = {'Rank': rank, 'Bib': s['bib'], 'Skater': s['name']}
        for race in RACES[:count]:
            row[LABELS[race]] = time_text(s['times'][race])
        row['Points'] = f'{points / 200:.3f}'
        row['First 500 lane'] = s['lanes']['500_1']
        row['First 1000 lane'] = s['lanes']['1000_1']
        rows.append(row)
    return rows


def results(case, race):
    ordered = sorted(case['skaters'], key=lambda s: s['times'][race])
    rows, previous, rank = [], None, 0
    for i, s in enumerate(ordered, 1):
        t = s['times'][race]
        if t != previous:
            rank = i
        previous = t
        rows.append({'Rank': rank, 'Bib': s['bib'], 'Skater': s['name'],
                     'Time': time_text(t), 'Lane': s['lanes'][race],
                     'Points': f'{t / (100 if distance(race) == 500 else 200):.3f}'})
    return rows


def answer_rows(case):
    by_bib = {s['bib']: s for s in case['skaters']}
    rows = []
    for i, (inner, outer) in enumerate(starting_pairs(case['skaters'], case['target']), 1):
        rows.append({'Pair': i, 'Inner bib': inner if inner is not None else '-',
                     'Inner skater': by_bib[inner]['name'] if inner is not None else '—',
                     'Outer bib': outer if outer is not None else '-',
                     'Outer skater': by_bib[outer]['name'] if outer is not None else '—'})
    return rows


def table_text(rows):
    columns = list(rows[0])
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in columns}
    return '\n'.join([' | '.join(c.ljust(widths[c]) for c in columns),
                      '-+-'.join('-' * widths[c] for c in columns)] +
                     [' | '.join(str(r[c]).ljust(widths[c]) for c in columns) for r in rows])


def worksheet(case, instructor=False):
    count = 2 if case['target'] == '500_2' else 3
    lines = ['SPRINT DRAW PRACTICE — ' + ('INSTRUCTOR' if instructor else 'PARTICIPANT'),
             '='*90, f"Case: {case['seed']} | Category: {case['gender']} | Level: {case['level']}",
             f"Skaters: {case['n']} | Exercise: {LABELS[case['target']]}",
             'All names and results are fictional. All entrants have valid completed races.',
             'Times: simulated indoor performances; no athlete-specific predictions.', '']
    for race in RACES[:count]:
        lines += [LABELS[race].upper(), table_text(results(case, race)), '']
    for c in range(2, count+1):
        lines += [f'CLASSIFICATION AFTER {c} DISTANCES', table_text(classification(case, c)), '']
    lines += ['EXERCISE', f"Create the start list for the {LABELS[case['target']].lower()}.",
              'Specify every pair in starting order, including I/O lanes and any solo.',
              'Explain the ranking used and how equal points are resolved.',
              'Reference: ISU Sports Rules (12 June 2026), Rule 240.4.2; Rule 244.7.', RULE_URL, '']
    if instructor:
        lines += ['OFFICIAL TRAINING ANSWER', table_text(answer_rows(case)), '',
                  f'Use total points after {count} distances.',
                  'Equal points: faster time in the first race of the distance concerned.',
                  'Reverse each skater’s starting lane relative to that first race.',
                  'Rank each lane group best first, match corresponding positions,',
                  'then reverse the pairs so the highest-ranked competitors start last.',
                  'A solo retains the required opposite lane, including an outer-lane solo.',
                  'Complete unresolved ties and incidents are outside this version’s scope.']
    return ('\n'.join(lines)+'\n').encode('utf-8')


def results_csv(case):
    count = 2 if case['target'] == '500_2' else 3
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=['Race', 'Rank', 'Bib', 'Skater', 'Time', 'Lane', 'Points'])
    writer.writeheader()
    for race in RACES[:count]:
        for row in results(case, race):
            writer.writerow({'Race': race, **row})
    return out.getvalue().encode('utf-8-sig')


def evaluate(entries, case):
    expected = starting_pairs(case['skaters'], case['target'])
    bibs = [b for pair in entries for b in pair if b is not None]
    required = {s['bib'] for s in case['skaters']}
    errors = []
    if len(bibs) != len(set(bibs)):
        errors.append('A skater may appear only once.')
    if set(bibs) != required:
        errors.append('Use every entered skater exactly once.')
    if any(i is None and o is None for i, o in entries):
        errors.append('Remove empty pairs.')
    if len(entries) != len(expected):
        errors.append(f'Create {len(expected)} pairs.')
    return {'errors': errors, 'correct': not errors and entries == expected,
            'correct_pairs': sum(a == b for a, b in zip(entries, expected)), 'total': len(expected)}


def streamlit_app():
    import streamlit as st
    st.set_page_config(page_title='Sprint Draw Practice', layout='wide')
    st.title('⛸️ Sprint Draw Practice')
    st.caption('Second 500 m or second 1000 m — fictional results, ISU Rule 240.4.2')
    with st.sidebar:
        gender = st.radio('Category', ['men', 'women'], format_func=str.title)
        target = st.selectbox('Create start list for', ['500_2', '1000_2'], format_func=LABELS.get)
        n = st.number_input('Number of skaters', 4, 40, 24)
        level = st.selectbox('Performance level', ['senior', 'junior'])
        tie = st.checkbox('Include equal total points',
                          help='The tied skaters started in the same lane in the first race of the distance concerned, so the tie-break affects their pairs.')
        seed_text = st.text_input('Case number (blank = random)')
        if st.button('Generate practice case', type='primary'):
            try:
                seed = int(seed_text) if seed_text.strip() else secrets.randbelow(2_000_000_000)
                st.session_state.case = generate_case(gender, n, seed, target, level, tie)
                st.session_state.rev = st.session_state.get('rev', 0)+1
                st.session_state.rows = 1
            except ValueError as exc:
                st.error(str(exc))
    if 'case' not in st.session_state:
        st.info('Choose settings and generate a practice case.')
        return
    case = st.session_state.case
    rev = st.session_state.rev
    count = 2 if case['target'] == '500_2' else 3
    st.success(f"Case #{case['seed']} — {case['gender'].title()} — {LABELS[case['target']]}")
    race_tab, standings_tab, exercise_tab, downloads_tab = st.tabs(
        ['Race results', 'Standings', 'Start-list exercise', 'Downloads'])
    with race_tab:
        for race in RACES[:count]:
            st.subheader(LABELS[race])
            st.dataframe(results(case, race), hide_index=True, width='stretch')
    with standings_tab:
        for c in range(2, count+1):
            st.subheader(f'Classification after {c} distances')
            st.dataframe(classification(case, c), hide_index=True, width='stretch')
    with exercise_tab:
        st.write(f"Create the starting pairs for the **{LABELS[case['target']].lower()}**.")
        st.caption('Add pairs as needed. A solo can start in I or O; leave the other lane empty.')
        names = {s['bib']: s['name'] for s in case['skaters']}
        def label(bib):
            return '— Empty lane —' if bib is None else f'{bib} — {names[bib]}'
        entries = []
        for row in range(st.session_state.rows):
            cols = st.columns([1, 4, 4])
            cols[0].write(f'Pair {row+1}')
            inner = cols[1].selectbox('Inner (I)', [None]+list(names), format_func=label, key=f'i_{rev}_{row}')
            outer = cols[2].selectbox('Outer (O)', [None]+list(names), format_func=label, key=f'o_{rev}_{row}')
            entries.append((inner, outer))
        a, b = st.columns(2)
        if a.button('+ Add pair', disabled=st.session_state.rows >= case['n']):
            st.session_state.rows += 1
            st.rerun()
        if b.button('− Remove last pair', disabled=st.session_state.rows <= 1):
            st.session_state.rows -= 1
            st.rerun()
        # Feedback is recomputed only for current entries, never stale after editing.
        if st.button('Check my starting pairs', type='primary'):
            result = evaluate(entries, case)
            if result['errors']:
                for error in result['errors']:
                    st.warning(error)
            elif result['correct']:
                st.success('Correct! All pairs, lane positions and starting order are right.')
            else:
                st.warning(f"{result['correct_pairs']} of {result['total']} pairs are correct.")
        if st.checkbox('Reveal correct start list', key=f'reveal_{rev}'):
            st.dataframe(answer_rows(case), hide_index=True, width='stretch')
            st.info('Use the overall classification, reverse the first-race lanes, pair by rank within each lane group, and start the best pair last.')
    with downloads_tab:
        st.subheader('Participant materials')
        st.download_button('Practice worksheet with results and classifications (TXT)', data=worksheet(case),
                           file_name=f"sprint_practice_{case['target']}_{case['seed']}.txt", mime='text/plain')
        st.download_button('Race results (CSV)', data=results_csv(case),
                           file_name=f"sprint_results_{case['seed']}.csv", mime='text/csv')
        st.subheader('Instructor materials')
        st.caption('Answers are available to everyone. This is a practice tool without instructor authentication.')
        if st.checkbox('Show instructor downloads', key=f'instructor_{rev}'):
            st.download_button('Answer report (TXT)', data=worksheet(case, True),
                               file_name=f"sprint_instructor_{case['target']}_{case['seed']}.txt", mime='text/plain')
            st.download_button('Complete case including all simulated races (JSON)',
                               data=json.dumps(case, ensure_ascii=False, indent=2).encode('utf-8'),
                               file_name=f"sprint_case_{case['seed']}.json", mime='application/json')
    st.caption('Unofficial training tool. Valid completed races only; no incidents or withdrawals. '
               'Same case number AND settings recreate the case. Rules: 12 June 2026.')


def main():
    parser = argparse.ArgumentParser(description='Generate sprint draw training materials.')
    parser.add_argument('--gender', choices=['men', 'women'], default='men')
    parser.add_argument('--skaters', type=int, default=24)
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--exercise', choices=['500_2', '1000_2'], default='500_2')
    parser.add_argument('--level', choices=['senior', 'junior'], default='senior')
    parser.add_argument('--tie', action='store_true')
    parser.add_argument('--output', type=Path, default=Path('sprint_output'))
    args = parser.parse_args()
    seed = args.seed if args.seed is not None else secrets.randbelow(2_000_000_000)
    case = generate_case(args.gender, args.skaters, seed, args.exercise, args.level, args.tie)
    args.output.mkdir(parents=True, exist_ok=True)
    stem = f'sprint_{args.exercise}_{seed}'
    (args.output / f'{stem}_participant.txt').write_bytes(worksheet(case))
    (args.output / f'{stem}_instructor.txt').write_bytes(worksheet(case, True))
    (args.output / f'{stem}_results.csv').write_bytes(results_csv(case))
    (args.output / f'{stem}_case.json').write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Case {seed}: files saved in {args.output.resolve()}')


if __name__ == '__main__':
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        in_streamlit = get_script_run_ctx(suppress_warning=True) is not None
    except ImportError:
        in_streamlit = False
    if in_streamlit:
        streamlit_app()
    else:
        main()
