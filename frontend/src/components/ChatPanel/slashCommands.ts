export interface SlashCommand {
  name: string
  description: string
  buildPrompt: (args: string) => string
}

export const SLASH_COMMANDS: SlashCommand[] = [
  {
    name: "save-recipe",
    description: "Save this conversation as a reusable recipe",
    buildPrompt: (args) => {
      const base =
        "Create a reusable recipe from this conversation using the save_as_recipe tool. " +
        "Analyze our conversation, extract the key steps, identify values that should become variables for reuse, and save it as a recipe."
      return args ? `${base}\n\n${args}` : base
    },
  },
]
