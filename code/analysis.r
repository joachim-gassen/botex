library(tidyverse)
library(modelsummary)
rounds <- read_csv("data/generated/rounds.csv")

datasummary(sent_amount + sent_back_amount ~ experiment*(N + mean + sd + median), data = rounds)
t.test(rounds$sent_amount ~ rounds$experiment)
wilcox.test(rounds$sent_amount ~ rounds$experiment)
t.test(rounds$sent_back_amount ~ rounds$experiment)
wilcox.test(rounds$sent_back_amount ~ rounds$experiment)
ggplot(rounds, aes(x = experiment, y = sent_amount, group = experiment, color = experiment)) +
  geom_boxplot() +
  labs(title = "Sent Amount by Experiment",
       x = "",
       y = "Sent Amount"
    ) +
  theme_minimal() +
	theme(legend.position = "bottom")
