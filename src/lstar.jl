#!/usr/bin/env julia
import Random: Xoshiro
include("args.jl")
include("api.jl")


struct LstarHypothesis
    abc::Vector{String}
    pfx::Vector{String}
    sm::Dict{Tuple{Int,String},Int}
    out::Dict{String,Int}
end


function predict(h::LstarHypothesis, s::AbstractString)
    q, i = "", 1
    while !isempty(s)
        for c in h.abc
            if startswith(s, c)
                q *= c
                s = chopprefix(s, c)
                i = h.sm[(i, c)]
                break
            end
        end
    end
    return h.out[h.pfx[i]]
end


function lstar(f, abc; seed=nothing)
    rng = Xoshiro(seed)
    pfx = [""]
    sfx = [""]
    tbl = Dict(""=>f(""))
    getrows() = Dict(p=>[tbl[p*s] for s in sfx] for p in pfx)

    function query!(s)
        get!(tbl, s) do
            f(s)
        end
    end

    function makehypothesis()
        rows = Dict(p*k=>[tbl[p*k*s] for s in sfx] for p in pfx for k in ["";abc])
        ps = unique(p->rows[p], pfx)
        rs = Dict(rows[p]=>i for (i,p) in enumerate(ps))
        sm = Dict((i,c)=>rs[rows[p*c]] for (i,p) in enumerate(ps) for c in abc)
        LstarHypothesis(abc, ps, sm, tbl)
    end

    function checkclosed()
        rows = getrows()
        for p in pfx, c in abc
            a = query!.((p*c) .* sfx)
            k = findfirst(==(a), rows)
            if isnothing(k)
                push!(pfx, p*c)
                query!.((p*c) .* sfx)
                return false
            end
        end
        return true
    end

    function checkconsistent()
        rows = getrows()
        for p in pfx, q in pfx
            q <= p && continue
            if rows[p] == rows[q]
                for c in abc, s in sfx
                    if query!(p*c*s) != query!(q*c*s)
                        push!(sfx, c*s)
                        query!.(pfx .* (c*s))
                        return false
                    end
                end
            end
        end
        return true
    end

    function checkhypothesis()
        hyp = makehypothesis()
        rows = getrows()
        qs = ws = copy(pfx)
        for _ in 1:4, c in abc
            ws = [q*c for q in ws]
            append!(qs, ws)
        end
        for (q,s) in Iterators.product(qs, sfx)
            if predict(hyp, q*s) != query!(q*s)
                for p in Iterators.accumulate(*, q)
                    if p ∉ pfx
                        push!(pfx, p)
                        query!.(p .* sfx)
                    end
                end
                return false
            end
        end
        return true
    end

    while true
        checkclosed() || continue
        checkconsistent() || continue
        checkhypothesis() || continue
        break
    end
    hyp = makehypothesis()
end


function makeguess(h::LstarHypothesis)
    hs = Dict()
    for ((i,c),j) in h.sm
        (i,c) ∈ keys(hs) && continue
        for (k,q) in findall(==(i), h.sm)
            if k == j && (k,q) ∉ keys(hs)
                hs[(i,c)] = (k, q)
                hs[(k,q)] = (i, c)
                break
            end
        end
    end
    halls = Dict((i,parse(Int,c))=>(j,parse(Int,d))
        for ((i,c),(j,d)) in hs)

    rooms = [h.out[p] for p in h.pfx]
    start = 0
    cons = [
        Dict("from"=>Dict("room"=>i-1, "door"=>c),
            "to"=>Dict("room"=>j-1, "door"=>d))
        for ((i,c),(j,d)) in halls
    ]
    Dict{String,Any}(
        "rooms"=>rooms,
        "startingRoom"=>start,
        "connections"=>cons)
end


function @main(args)
    args = parseargs(args)
    api = ApiSession(args.url)
    api_select(api, args.problem, seed=args.seed)
    hyp = lstar(string.(0:5), seed=args.seed) do s
        r = api_explore(api, [s])
        r["results"][1][end]
    end
    guess = makeguess(hyp)
    @show guess["rooms"]
    r = api_guess(api, guess)
    @show r
    return 0
end
