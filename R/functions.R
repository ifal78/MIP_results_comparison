
read_mip_tables <- function(scen_name, mod_dirs, tab = "^resource.capacity.csv(.gz)?$") {
  ll <- lapply(mod_dirs, function(d) {
    f <- list.files(fp(scen_name, d), pattern = tab)
    fname <- fp(scen_name, d, f)
    if (length(fname) > 1) {
      f_time <- file.info(fname)$mtime
      ii <- f_time == max(f_time)
      message("Ignoring:\n", paste(basename(fname[!ii]), sep = "\n"))
      fname <- fname[ii]
    }
    cat(d, fname, "\n")
    x <- fread(fname)
    dval <- duplicated(x)
    if (any(dval)) message(sum(dval), " duplicated values")
    x <- x[!dval,]
    if (any(grepl("(start|end)_MWh", names(x)))) {
      y <- x |>
        select(-any_of(c("start_value", "end_value"))) |>
        filter((!is.na(start_MWh) & start_MWh > 0) | !is.na(end_MWh)) |>
        rename(
          start_value = start_MWh,
          end_value = end_MWh
        ) |>
        mutate(unit = "MWh")
      x <- x |>
        select(-any_of(c("start_MWh", "end_MWh"))) |>
        bind_rows(y)
    }
    if (!is.null(x[["hour"]])) {
      if (min(x$hour) == 1) x$hour <- x$hour - 1
    }
    x |> mutate(case = scen_name)
  })
  ll
}


add_tech_type <- function(x) {
  # browser()
  x %>%
    # left_join(resource_mapping2, by = c("process" = "resource_name")) %>%
    # mutate(tech_type = if_else(is.na(tech_type), process, tech_type)) %>%
    mutate(
      tech_type = resource_name,
      tech_type = if_else(grepl("batter", tech_type), "Battery", tech_type),
      tech_type = if_else(grepl("batter", tech_type), "Battery", tech_type),
      tech_type = if_else(grepl("hydro.+pumped", tech_type),
                          "Hydroelectric Pumped Storage", tech_type),
      tech_type = if_else(grepl("conventional.hydroelectric", tech_type),
                          "Conventional Hydroelectric", tech_type),
      tech_type = if_else(grepl("small.hydroelectric", tech_type),
                          "Small Hydroelectric", tech_type),
      tech_type = if_else(grepl("biomass", tech_type), "Biomass", tech_type),
      tech_type = if_else(grepl("landbased.?wind|onshore", tech_type),
                          "Onshore Wind", tech_type),
      tech_type = if_else(grepl("offshore.?wind", tech_type), "Offshore Wind", tech_type),
      # tech_type = if_else(grepl("shore.wind", tech_type), "Wind", tech_type),
      tech_type = if_else(grepl("utilitypv|solar|photovoltaic", tech_type),
                          "Solar", tech_type),
      tech_type = if_else(grepl("ccccs", tech_type), "CCS", tech_type),
      tech_type = if_else(grepl("natural.?gas", tech_type), "Natural Gas",
                          tech_type),
      tech_type = if_else(grepl("coa", tech_type), "Coal", tech_type),
      tech_type = if_else(grepl("distributed.?generation", tech_type),
                          "Distributed Generation", tech_type),
      tech_type = if_else(grepl("geothermal", tech_type), "Geothermal", tech_type),
      tech_type = if_else(grepl("uclear", tech_type), "Nuclear", tech_type),
      tech_type = if_else(grepl("hydrogen", tech_type), "Hydrogen", tech_type),
      tech_type = if_else(grepl("petroleum.?liquids", tech_type), "Petroleum Liquids",
                          tech_type),

    )
}

# read_all_csv <- function(fname, cases, models) {
#   ll <- lapply(cases, function(cs) {
#     ll <- lapply(models, function(m) {
#       mod <- list.files(cs, pattern = m, ignore.case = T, include.dirs = T,
#                         recursive = F, full.names = F)
#       if (length(mod) == 0) return()
#       fread(file.path(cs, mod, fname))
#     })
#     rbindlist(ll, use.names = T, fill = T) |>
#       mutate(ucase = cs, .before = 1)
#   })
#   rbindlist(ll, use.names = T, fill = T)
# }

fp <- file.path

# scen_name <- "26z-short-base-50"

fModDirs <- function(scen_name, pattern = "results") {
  # list.dirs(scen_name, full.names = F, recursive = F)
  list.files(scen_name, pattern, include.dirs = T)
}

fModNames <- function(mod_dirs, pattern = ".*?(?=.results)") {
  # sub("^(.*?).results.*", "\\1", mod_dirs)
  str_extract(mod_dirs, pattern)
}

