library(tidyverse)
library(ggbeeswarm)
library(modelsummary)

rounds <- read_csv("data/generated/rounds.csv", show_col_types = FALSE)
participants <- read_csv("data/generated/participants.csv", show_col_types = FALSE)
rounds$pct_returned <- rounds$sent_back_amount/(3*rounds$sent_amount)

datasummary(sent_amount + sent_back_amount + pct_returned ~ experiment*(N + mean + sd + median), data = rounds)
t.test(rounds$sent_amount ~ rounds$experiment)
wilcox.test(rounds$sent_amount ~ rounds$experiment)
t.test(rounds$sent_back_amount ~ rounds$experiment)
wilcox.test(rounds$sent_back_amount ~ rounds$experiment)
t.test(rounds$pct_returned ~ rounds$experiment)
wilcox.test(rounds$pct_returned ~ rounds$experiment)

color_scale <- RColorBrewer::brewer.pal(3 ,"Set1")
names(color_scale) <- unique(rounds$experiment)
color_scale_labs <- c("Investor/Manager", "Neutral")

ggplot(rounds, aes(x = experiment, y = sent_amount, group = experiment, color = experiment)) +
  geom_boxplot() +
	geom_beeswarm(size = 0.25) +
  labs(title = "Sent Amount by Framing",
       x = "",
       y = ""
    ) +
	scale_x_discrete(labels = NULL, breaks = NULL) +
	scale_color_manual("", values = color_scale, labels = color_scale_labs) +
	theme_minimal() +
	theme(
		legend.position = "bottom", 
		panel.grid.minor = element_blank()
	)

ggplot(rounds, aes(x = as.factor(round), y = sent_amount, group = experiment, color = experiment)) +
	geom_beeswarm(size = 0.25, corral = "wrap") +
	stat_summary(
		aes(fill = experiment), color = NA, 
		geom = "ribbon", fun = "mean", alpha=0.1,
		fun.min = function(x) mean(x) - 1.96 / (length(x) - 1) * sd(x), 
		fun.max = function(x) mean(x) + 1.96 / (length(x) - 1) * sd(x),
		show.legend = FALSE
	) + 
	labs(
		title = "Sent Amount by Framing and Round",
		x = "Round",
		y = "",
		color = "",
	) +
	scale_color_manual("", values = color_scale, labels = color_scale_labs) +
	scale_fill_manual("", values = color_scale, labels = color_scale_labs) +
	theme_minimal() +
	theme(
		legend.position = "bottom", 
		panel.grid.major.x  = element_blank(),
		panel.grid.minor = element_blank()
	)


modelsummary(
	lm(sent_amount ~ round*experiment, data = rounds),
	stars = c(`***` = 0.01, `**` = 0.05, `*` = 0.1),
	gof_omit = "BIC|AIC|F|RMSE|Log"
)

datasummary(payoff ~ experiment*(N + mean + sd + median), data = participants)
t.test(participants$payoff ~ participants$experiment)
wilcox.test(participants$payoff ~ participants$experiment)
participants$role = ifelse(participants$role_in_group == 1, "Sender", "Receiver")
modelsummary(
	lm(payoff ~ experiment*role, data = participants),
	stars = c(`***` = 0.01, `**` = 0.05, `*` = 0.1),
	gof_omit = "BIC|AIC|F|RMSE|Log"
)



