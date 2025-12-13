import Downloads: Downloads, Downloader
import JSON
import URIs: URI, absuri


struct ApiSession
    baseurl::URI
    pool::Downloader
    verbose::Bool
    function ApiSession(baseurl::AbstractString; verbose=false)
        new(URI(baseurl), Downloader(), verbose)
    end
end


function apipost(api::ApiSession, url::AbstractString, obj)
    url = absuri(url, api.baseurl)
    data = JSON.json(obj)
    api.verbose && println(stderr, "POST $url $data")
    io = IOBuffer()
    oi = IOBuffer(data)
    headers = ["Content-Type"=>"application/json"]
    r = Downloads.request(string(url), input=oi, output=io,
        method="POST", headers=headers, downloader=api.pool)
    s = String(take!(io))
    api.verbose && println(stderr, s)
    return s |> JSON.parse
end


api_select(api::ApiSession, name::AbstractString) =
    apipost(api, "/select", Dict("problemName"=>name))

api_select(api::ApiSession, name::AbstractString; seed::Nothing) =
    apipost(api, "/select", Dict("problemName"=>name))

api_select(api::ApiSession, name::AbstractString; seed::Any) =
    apipost(api, "/select", Dict("problemName"=>name, "seed"=>seed))

api_explore(api::ApiSession, plans::AbstractVector{<:AbstractString}) =
    apipost(api, "/explore", Dict("plans"=>plans))

api_guess(api::ApiSession, guess::AbstractDict) =
    apipost(api, "/guess", Dict("map"=>guess))
