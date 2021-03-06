import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell as celln
import data
from colour import Color
from typing import List, Tuple
from solver import ShiftSolver

def get_days(shifts):
    """Get the list of day names, in order,
    from a shift tuple list.
    """
    unique_days = []
    for d, s in shifts.keys():
        del s
        if d not in unique_days:
            unique_days.append(d)
    return unique_days

def get_prefcolor(n, max_n):
    """Takes a pref score, and a worst pref score,
    and returns a color to format how good that pref score is.
    Args:
        n: the pref score
        max_n: the worst pref score for that shift
    Returns:
        color: long hex color
    """
    assert n <= max_n
    good = Color('#bef7c5')
    bad = Color('#ffd9d9')
    return list(good.range_to(bad, max_n + 1))[n].hex_l

def get_people(preferences):
    return sorted(list(set([p for d,s,p in preferences.keys()])))

def write_to_file(filename, shifts, preferences, assignments, personal_reqs):
    """Write the solver result to an Excel workbook
    Args:
        shifts: dict of sdata[day_id, shift_id] = {
            'capacity': 2,
            'begin': 525,
            'end': 960
            }
        prefs: dict of preferences[day_id,shift_id,person_id] = pref_score 
        assignments: dict of assigned[day_id,shift_id,person_id] = True | False
        personal_reqs: dict of preqs[person_id] = {
            'min': n1, 
            'max': n2, 
            'min_long_shifts': n3, 
            'only_long_shifts': bool1
            }
    """
    workbook = xlsxwriter.Workbook(filename)
    shifts_ws = workbook.add_worksheet(name="shifts")
    time_f = workbook.add_format({'num_format': 'hh:mm'})
    
    # Shifts
    n_shifts = len(shifts)
    ## Headers
    for idx, txt in enumerate(["Day", "ShiftID", "Capacity", "Begin", "End", "strID", "length in hours"]):
        shifts_ws.write(0, idx, txt)

    for rowidx, ((d,s), sdata) in enumerate(shifts.items(), start=1):
        shifts_ws.write(rowidx, 0, d) # Day
        shifts_ws.write(rowidx, 1, s) # ShiftId
        shifts_ws.write(rowidx, 2, sdata['capacity']) # Capacity
        shifts_ws.write(rowidx, 3, sdata['begin']/(24*60), time_f) # Begin time
        shifts_ws.write(rowidx, 4, sdata['end']/(24*60), time_f) # End time
        shifts_ws.write(rowidx, 5, str(d)+str(s)) # strID - should be unique
        shifts_ws.write_formula(rowidx, 6, f'=({celln(rowidx, 4, col_abs=True)}-{celln(rowidx, 3, col_abs=True)})*24') # shift length

    # Preferences
    people = get_people(preferences)
    n_people = len(people)
    percentage_format = workbook.add_format({'num_format': '0.00%'})
    
    # Add default none values to preferences dict
    for d,s in shifts.keys():
        for p in people:
            if (d,s,p) not in preferences.keys():
                preferences[d,s,p] = None

    # Write to the sheet
    pref_ws = workbook.add_worksheet(name="preferences")
    pref_ws.protect()
    ## Headers
    for idx, txt in enumerate(["strID"] + people):
        pref_ws.write(0, idx, txt)
    for rowidx, (d,s) in enumerate(shifts.keys(), start=1):
        pref_ws.write(rowidx, 0, str(d)+str(s)) # strID
        for colidx, p in enumerate(people, start=1):
            pref_ws.write(rowidx, colidx, preferences[d,s,p])
    
    ## % of shifts registered to last row
    pref_ws.write(n_shifts+1,0, "Registered%")
    for pidx in range(1, n_people + 1):
        pref_ws.write_formula(n_shifts + 1, pidx,
        ''.join(f'''=IF(
                NOT(
                    VLOOKUP({celln(0, pidx)},
                    personal_reqs!{celln(1,0)}:{celln(n_people,4)},
                    5)
                ),
                COUNT({celln(1,pidx)}:{celln(n_shifts,pidx)})/{n_shifts},
                COUNT({celln(1,pidx)}:{celln(n_shifts,pidx)})/COUNTIF(assignments!{celln(1,n_people+3)}:{celln(n_shifts,n_people+3)},"Long")
            )
            '''.split()), cell_format=percentage_format)


    # Personal requirements
    pers_ws = workbook.add_worksheet(name="personal_reqs")
    ## Headers
    for idx, txt in enumerate(["person","Min. hours", "Max. hours","Min. long shits","Only long shifts"]):
        pers_ws.write(0, idx, txt)
    for rowidx, p in enumerate(people, start=1):
        pers_ws.write(rowidx, 0, p)
        pers_ws.write_number(rowidx, 1, personal_reqs[p]['min'])
        pers_ws.write_number(rowidx, 2, personal_reqs[p]['max'])
        pers_ws.write_number(rowidx, 3, personal_reqs[p]['min_long_shifts'])
        pers_ws.write_boolean(rowidx, 4, personal_reqs[p]['only_long_shifts'])

    # Assignments

    # Formats
    no_pref = workbook.add_format({'font_color':'#dedede'})

    assign_ws = workbook.add_worksheet(name="assignments")
    # Write to the sheet
    ## Headers
    for idx, txt in enumerate(["strID"] + people + ["n assigned", "capacity", "Is long"]):
        assign_ws.write(0, idx, txt)

    for rowidx, (d,s) in enumerate(shifts.keys(), start=1):
        assign_ws.write(rowidx, 0, str(d)+str(s)) # strID
        for colidx, p in enumerate(people, start=1):
            if preferences[d,s,p] is None:
                assign_ws.write_boolean(rowidx, colidx, assignments[d,s,p], no_pref)
            else:
                pref_color = get_prefcolor(preferences[d,s,p], max([preferences[d,s,p] for p in people if preferences[d,s,p] is not None]))
                pref_format = workbook.add_format({'bg_color':pref_color})
                assign_ws.write_boolean(rowidx, colidx, assignments[d,s,p], pref_format)
    # Add formula t calculate number of empty shifts
    assign_ws.write(n_shifts+1,n_people+1, 'Empty shifts')
    assign_ws.write_formula(n_shifts+1,n_people+2, f'=COUNTIF({celln(1,n_people+1)}:{celln(n_shifts,n_people+1)},0)')
    # Add formula to calculate number of empty places in shifts
    assign_ws.write(n_shifts+2,n_people+1, 'Empty places on shifts')
    assign_ws.write_formula(n_shifts+2,n_people+2, f'=SUM({celln(1,n_people+2)}:{celln(n_shifts,n_people+2)})-SUM({celln(1,n_people+1)}:{celln(n_shifts,n_people+1)})')
    # Add total pref score
    assign_ws.write(n_shifts+3,n_people+1, 'Pref score')
    assign_ws.write(n_shifts+3,n_people+2,f'=SUM({celln(n_shifts+7,1)}:{celln(n_shifts+7,n_people)})')

    # Add shift capacity condition indicator
    ## Add a formula to the end of each row,
    ## to calculate the number of people assigned.
    ## Add conditional formatting to this cell,
    ## so that it's:
    ##      green,  when the shift is full
    ok_format =      workbook.add_format({'bg_color':'#a6ff9e'})
    ##      orange, when the shift is below capacity
    medium_format = workbook.add_format({'bg_color': '#ffc670'})
    ##      red,    when the shift is over capacity
    bad_format =  workbook.add_format({'bg_color': '#ff7a70'})
    for rowidx, (d,s) in enumerate(shifts.keys(), start=1):
        # Current shift state
        cap_format = workbook.add_format({'left':1})
        assign_ws.write_formula(
            rowidx, n_people+1, 
            f'=COUNTIF({celln(rowidx, 1)}:{celln(rowidx,n_people)}, TRUE)',
            cap_format)
        # Capacity
        assign_ws.write_formula(
            rowidx, n_people+2,
            f'=shifts!C{rowidx+1}')
        assign_ws.write_formula(
            rowidx, n_people+3,
            f'=IF(INDEX(shifts!{celln(1,0)}:{celln(n_shifts,6)},MATCH(assignments!{celln(rowidx,0)},assignments!{celln(1,0)}:{celln(n_shifts,0)},0),7)>5,"Long", "")'
        )

        #region Conditional formatting the n_people on shift
        capacity_col_row = celln(rowidx, n_people+2)
        # Full
        assign_ws.conditional_format(celln(rowidx, n_people+1),
        {
            'type':'cell',
            'criteria':'==',
            'value': capacity_col_row,
            'format': ok_format
        })
        # Below capacity
        assign_ws.conditional_format(celln(rowidx, n_people+1),
        {
            'type':'cell',
            'criteria':'<',
            'value': capacity_col_row,
            'format': medium_format
        })
        # Full
        assign_ws.conditional_format(celln(rowidx, n_people+1),
        {
            'type':'cell',
            'criteria':'>',
            'value': capacity_col_row,
            'format': bad_format
        })
        #endregion  

    # Add personal requirement indicator
    ## For each person, under their last shift, indicate their:
    ## Minimum hours (from the personal_reqs sheet)
    ## The actual number of hours they are taking
    ## Maximum hours (from the personal_reqs sheet)
    ## Number of long shifts taken
    ## Minimum number of long shifts (from the personal_reqs sheet)
    ## Whether they only take long shifts (from the personal_reqs sheet)

    # Horrifying excel formula #1
    def preq_formula(person_col, var_col):
        return (f'=INDEX(personal_reqs!{celln(1,0, row_abs=True, col_abs=True)}:{celln(n_people,4, row_abs=True, col_abs=True)},'+
            f'MATCH({celln(0,person_col, row_abs=True)},personal_reqs!{celln(1,0, row_abs=True, col_abs=True)}:{celln(n_people, 0, row_abs=True, col_abs=True)},0)'
            +f',{var_col})')

    def workhours_formula(person_col):
        return (f'=SUMIF({celln(1,person_col, row_abs=True)}:{celln(n_shifts, person_col, row_abs=True)},TRUE,shifts!{celln(1,6, row_abs=True, col_abs=True)}:{celln(n_shifts,6, row_abs=True, col_abs=True)})')

    def pref_score_formula(person_col):
        return f'=SUMIF(assignments!{celln(1,person_col, row_abs=True)}:{celln(n_shifts,person_col, row_abs=True)},TRUE,preferences!{celln(1,person_col, row_abs=True)}:{celln(n_shifts,person_col, row_abs=True)})'

    # TODO minor formatting here

    # Row headers
    for row_idx, txt in enumerate(["Min. hours", 
                         "Actual hours", 
                         "Max. hours", 
                         "Long shifts taken", 
                         "Min. long shifts", 
                         "Long shifts only",
                         "Pref score"
                            ]):
        r0 = n_shifts+1
        assign_ws.write(r0+row_idx, 0, txt)

    for col_idx, p in enumerate(people, start=1):
        r0 = n_shifts+1 # Start after the last shift
        min_hours_formula = preq_formula(col_idx, 2)
        assign_ws.write_formula(r0, col_idx, min_hours_formula)
        assign_ws.write_formula(r0+1, col_idx, workhours_formula(col_idx))
        max_hours_formula = preq_formula(col_idx, 3)
        assign_ws.write_formula(r0+2, col_idx, max_hours_formula)
        assign_ws.write_formula(r0+3, col_idx, f'=COUNTIFS({celln(1,col_idx)}:{celln(n_shifts,col_idx)},TRUE,{celln(1, n_people+3)}:{celln(n_shifts, n_people+3)},"Long")')
        min_long_shifts_formula = preq_formula(col_idx, 4)
        assign_ws.write_formula(r0+4, col_idx, min_long_shifts_formula)
        long_shifts_only_formula = preq_formula(col_idx, 5)
        assign_ws.write_formula(r0+5, col_idx, long_shifts_only_formula)
        assign_ws.write_formula(r0+6, col_idx, pref_score_formula(col_idx))

        # Add conditional to show if hours is withing range
        assign_ws.conditional_format(celln(r0+1,col_idx),
        {
            'type':'cell',
            'criteria':'between',
            'minimum': celln(r0,col_idx),
            'maximum': celln(r0+2,col_idx),
            'format': ok_format
        })
        assign_ws.conditional_format(celln(r0+1,col_idx),
        {
            'type':'cell',
            'criteria':'not between',
            'minimum': celln(r0,col_idx),
            'maximum': celln(r0+2,col_idx),
            'format': bad_format
        })

    # Add conditional to highlight actual applications
    applied_shift_format = workbook.add_format({
        'bold': True,
        'border': 1
    })

    assign_ws.conditional_format(0,0, n_shifts+1, n_people+1,
        {
            'type': 'cell',
            'criteria': '==',
            'value': True,
            'format': applied_shift_format
        }
    )

    # Master view
    master = workbook.add_worksheet(name='sensei-view')
    for col_idx, txt in enumerate(["strID", 
                         "Begin", 
                         "End", 
                         "Person", 
                         "Works"
                            ]):
        master.write(0, col_idx, txt) # TODO hide works columns
    
    for scount, ((d,s), sdata) in enumerate(shifts.items()):
        for pcount, person in enumerate(people):
            r_index = scount*n_people+pcount + 1
            master.write(r_index, 0, str(d)+str(s))
            master.write(r_index, 1, sdata['begin']/(24*60), time_f)
            master.write(r_index, 2, sdata['end']/(24*60), time_f)
            master.write(r_index, 3, person)
            assignments_range = f'assignments!{celln(1,1)}:{celln(n_shifts, n_people)}'
            shiftname_addr = f'{celln(r_index, 0)}'
            shiftids_range = f'assignments!{celln(1,0)}:{celln(n_shifts,0)}'
            pname_addr = f'{celln(r_index, 3)}'
            names_range = f'assignments!{celln(0,1)}:{celln(0, n_people)}'
            master.write_formula(r_index, 4, f'=INDEX({assignments_range},MATCH({shiftname_addr},{shiftids_range},0),MATCH({pname_addr},{names_range},0))')

    master.autofilter(0,4,0,4)
    master.filter_column(4, "Works == TRUE")

    # Worker view
    worker = workbook.add_worksheet(name='padawan-view')
    for col_idx, txt in enumerate([
                        "Person",
                        "strID", 
                        "Begin", 
                        "End",  
                        "Works"
                            ]):
        worker.write(0, col_idx, txt) # TODO hide works columns
    for pcount, person in enumerate(people):
        for scount, ((d,s), sdata) in enumerate(shifts.items()):
            r_index = pcount*n_shifts+scount + 1
            worker.write(r_index, 0, person)
            worker.write(r_index, 1, str(d)+str(s))
            worker.write(r_index, 2, sdata['begin']/(24*60), time_f)
            worker.write(r_index, 3, sdata['end']/(24*60), time_f)
            assignments_range = f'assignments!{celln(1,1)}:{celln(n_shifts, n_people)}'
            shiftname_addr = f'{celln(r_index, 1)}'
            shiftids_range = f'assignments!{celln(1,0)}:{celln(n_shifts,0)}'
            pname_addr = f'{celln(r_index, 0)}'
            names_range = f'assignments!{celln(0,1)}:{celln(0, n_people)}'
            worker.write_formula(r_index, 4, f'=INDEX({assignments_range},MATCH({shiftname_addr},{shiftids_range},0),MATCH({pname_addr},{names_range},0))')

    worker.autofilter(0,0,0,4) # For the your name
    worker.filter_column(4, "Works == TRUE")


    workbook.close()

def write_summary(filename: str, rows: Tuple[str, ShiftSolver]):
    """Creates an excel worksheet to a new file showing the properties of the solves,
    with links to them.
    Args:
        filename: to create the workbook at
        rows: list of (xlsxfilepath, solver) tuples
    """
    workbook = xlsxwriter.Workbook(filename)
    
    hour_format = workbook.add_format({'num_format': '#,##0.00'})

    ws = workbook.add_worksheet('index')
    for cidx, txt in enumerate(
        ['Prefscore', 
        'Average prefscore/person', 
        'Mode of prefscores', 
        'Empty Shifts', 
        'Unfilled Hours',
        'Unfilled Hours (%)',
        'Unfilled Capacities', 
        'Unfilled Capacities (%)', 
        'Marginal prefence cost of capacity (f\')', 
        'Link to Solve']):
        ws.write(0, cidx, txt)

    percentage_format = workbook.add_format({'num_format': '0.00%'})
    dec_format = workbook.add_format({'num_format': '0.00'})
    is_first_row = True
    for rowidx, (solutionpath, solver) in enumerate(rows, start=1):
        for colidx, (val, format_) in enumerate(
            [(solver.PrefScore(),None),
            (f'={(c_pref := celln(rowidx,0))}/{(c_n_all_people := celln(4,11))}', dec_format),
            (",".join(list(map(str,solver.PrefModes()))), None),
            (solver.EmptyShifts(), None),
            (solver.UnfilledHours(), hour_format),
            (f'={(c_hours := celln(rowidx, 4))}/{(c_n_all_hours := celln(3,11))}', percentage_format),
            (solver.UnfilledCapacities(), None),
            (f'={(c_caps := celln(rowidx, 6))}/{(c_n_all_caps := celln(2,11))}', percentage_format),
            (f'=IF(ISNUMBER({(c_caps_prev := celln(rowidx-1, 6))}),IF(AND((({c_caps_prev}-{c_caps})<>0),(({(c_pref_prev := celln(rowidx-1,0))}-{c_pref})<>0)),(-({c_pref}-{c_pref_prev})/({c_caps}-{c_caps_prev})),0),"")', None)
            ]
        ):
            ws.write(rowidx, colidx, val, format_)
        ws.write_url(rowidx, colidx+1, solutionpath)
    
    marginal_cost_chart = workbook.add_chart({'type':'line'})
    marginal_cost_chart.add_series({'values': f'=index!{celln(0, 8)}:{celln(len(rows), 8)}'})
    marginal_cost_chart.set_title({'name': 'Marginal cost for each solve'})
    marginal_cost_chart.set_legend({'none': True})
    ws.insert_chart('M3', marginal_cost_chart)

    try:
        # Use the first solution, these values should be equal everywhere
        solver = rows[0][1]
        ws.write(1, 10, "Number of shifts")
        ws.write_number(1,11, solver.NShifts())
        ws.write(2, 10, "Number of capacities")
        ws.write_number(c_n_all_caps, solver.NCapacities())
        ws.write(3, 10, "Number of hours")
        ws.write_number(c_n_all_hours, solver.Hours())
        ws.write(4, 10, "Number of people")
        ws.write_number(c_n_all_people, solver.NPeople())
    except IndexError:
        # No solutions
        pass

    workbook.close()
