# analysis/healing_metrics.R
# Usage: run after you have logs in runs/
library(tidyverse)
library(stringr)

files <- list.files("runs", pattern = "\\.log$", full.names = TRUE)

parse_log <- function(p) {
  lines <- readr::read_lines(p)
  tibble(
    run = basename(p),
    heals = sum(str_detect(lines, regex("heal.success=true", ignore_case = TRUE))),
    failures = sum(str_detect(lines, regex("heal.success=false", ignore_case = TRUE)))
  )
}

df <- purrr::map_dfr(files, parse_log)

print(df)

summary_df <- df |>
  summarise(
    runs = n(),
    healing_runs = sum(heals > 0),
    healing_rate = healing_runs / runs
  )
print(summary_df)

ggplot(df, aes(x = run, y = heals)) +
  geom_col() +
  labs(title = "Healenium healing events per run", x = "Run", y = "Heals") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))
