const _DefaultServerUrl = "http://localhost:8000"

const _usage = "solve.jl [-u URL] [-s SEED] <problem>\n"

const _help_page = """
    solve.jl [-u URL] [-s SEED] <problem>

    Positional arguments:
      problem   problem name

    Options:
      -u,--url      server URL (default: $(_DefaultServerUrl))
      -s,--seed     problem seed
      -h,--help     this help page
    """

function argerror(message)
    print(stderr, _usage)
    error(message)
end


function parseargs(args)
    problem = nothing
    url = nothing
    seed = nothing
    state = 0
    for arg in args
        if state == 0
            if startswith(arg, "-")
                if arg == "-h" || args == "--help"
                    print(_help_page); exit()
                elseif arg == "-u" || arg == "--url"
                    state = 1
                elseif arg == "-s" || arg == "--seed"
                    state = 2
                end
            else
                problem = arg
            end
        elseif state == 1
            url = arg
            state = 0
        elseif state == 2
            x = tryparse(Int, arg)
            seed = isnothing(x) ? arg : x
            state = 0
        end
    end
    if state == 1
        argerror("option needs a value: --url")
    elseif state == 2
        argerror("option needs a value: --seed")
    end
    isnothing(problem) && argerror("missing argument: problem")
    isnothing(url) && (url = _DefaultServerUrl)
    (; url, problem, seed)
end

