from __future__ import print_function

import minizinc

from datetime import timedelta
from IPython.core import magic_arguments
from IPython.core.magic import (Magics, magics_class, cell_magic, line_cell_magic)

MznModels = {}


@magics_class
class MznMagics(Magics):

    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        '-s',
        '--statistics',
        action='store_true',
        help='Output statistics'
    )
    @magic_arguments.argument(
        '-m',
        '--solution-mode',
        choices=["return", "bind"],
        default="return",
        help='Whether to return solution(s) or bind them to variables'
    )
    @magic_arguments.argument(
        '-a',
        '--all-solutions',
        action='store_true',
        help='Return all solutions for satisfaction problems, intermediate solutions for optimisation problems. '
             'Implies -o. '
    )
    @magic_arguments.argument(
        '-t',
        '--time-limit',
        type=int,
        help='Time limit in milliseconds (includes compilation and solving)'
    )
    @magic_arguments.argument(
        '--solver',
        default="gecode",
        help='Solver to run'
    )
    @magic_arguments.argument(
        '--data',
        nargs='*',
        default=[],
        help='Data files'
    )
    @magic_arguments.argument(
        'model',
        nargs='*',
        default=[],
        help='Model to solve'
    )
    @line_cell_magic
    def minizinc(self, line, cell=None):
        """MiniZinc magic"""

        # Parse cell magic flags
        args = magic_arguments.parse_argstring(self.minizinc, line)
        if args.solver == "":
            print("No solver given")
            return
        try:
            solver = minizinc.Solver.lookup(args.solver)
        except:
            print("Solver not found")
            return

        all_solutions = True if args.all_solutions else False
        time_limit = timedelta(milliseconds=args.time_limit) if args.time_limit else None

        # Setup instance
        instance = minizinc.Instance(solver)
        for m in args.model:
            mzn = MznModels.get(m)
            if mzn is not None:
                args.model.remove(m)
                instance.add_string(mzn)
        if cell is not None:
            instance.add_string(cell)

        # Get required variables from the IPython environment
        errors = []
        for var in instance.input:
            if var in self.shell.user_ns.keys():
                instance[var] = self.shell.user_ns[var]
            else:
                errors.append("Variable " + var + " is undefined")
        if len(errors) > 0:
            print("\n".join(errors))
            return

        # Solve MiniZinc instance
        try:
            result = instance.solve(timeout=time_limit, all_solutions=all_solutions)
        except minizinc.MiniZincError as err:
            print("An error occurred:\n%s" % err.message)
            return

        # Process solutions
        if args.solution_mode == "return":
            if len(result) == 0:
                return None
            else:
                # TODO: Return direct result item (needs proper output first)
                if all_solutions:
                    return [ sol.assignments for sol in result._solutions ]
                return result._solutions[-1].assignments
        else:
            if len(result) == 0:
                print("No solutions found")
                return None
            else:
                solution = result._solutions[-1].assignments  # TODO: Iterate over result item (needs proper iterator first)
                for var in solution:
                    self.shell.user_ns[var] = solution[var]
                    print(var + "=" + str(solution[var]))

    @cell_magic
    def mzn_model(self, line, cell):
        args = magic_arguments.parse_argstring(self.minizinc, line)
        if not args.model:
            print("No model name provided")
            return
        elif len(args.model) > 1:
            print("Multiple model names provided")
            return

        MznModels[args.model[0]] = cell
        return


def check_minizinc():
    if minizinc.default_driver is None:
        return False
    print(minizinc.default_driver.minizinc_version)
    return True
