// The 'use server' directive is crucial for marking the file as a server-side module in Next.js.
'use server';

/**
 * @fileOverview Provides question suggestions for neuro-oncology images.
 *
 * - suggestQuestions - A function that suggests relevant questions based on uploaded images.
 * - SuggestQuestionsInput - The input type for the suggestQuestions function.
 * - SuggestQuestionsOutput - The return type for the suggestQuestions function.
 */

import {ai} from '@/ai/ai-instance';
import {z} from 'genkit';

const SuggestQuestionsInputSchema = z.object({
  imageDescriptions: z
    .array(z.string())
    .describe('A list of descriptions for the uploaded neuro-oncology images.'),
});

export type SuggestQuestionsInput = z.infer<typeof SuggestQuestionsInputSchema>;

const SuggestQuestionsOutputSchema = z.object({
  suggestedQuestions: z
    .array(z.string())
    .describe('A list of suggested questions about the neuro-oncology images.'),
});

export type SuggestQuestionsOutput = z.infer<typeof SuggestQuestionsOutputSchema>;

export async function suggestQuestions(input: SuggestQuestionsInput): Promise<SuggestQuestionsOutput> {
  return suggestQuestionsFlow(input);
}

const prompt = ai.definePrompt({
  name: 'suggestQuestionsPrompt',
  input: {
    schema: z.object({
      imageDescriptions: z
        .array(z.string())
        .describe('A list of descriptions for the uploaded neuro-oncology images.'),
    }),
  },
  output: {
    schema: z.object({
      suggestedQuestions: z
        .array(z.string())
        .describe('A list of suggested questions about the neuro-oncology images.'),
    }),
  },
  prompt: `You are an AI assistant specialized in neuro-oncology. Based on the description of the uploaded neuro-oncology images, suggest a list of relevant questions that a user might want to ask to understand the images better. Provide 5 questions.

Image Descriptions: {{{imageDescriptions}}}

Suggested Questions:`,
});

const suggestQuestionsFlow = ai.defineFlow<
  typeof SuggestQuestionsInputSchema,
  typeof SuggestQuestionsOutputSchema
>({
  name: 'suggestQuestionsFlow',
  inputSchema: SuggestQuestionsInputSchema,
  outputSchema: SuggestQuestionsOutputSchema,
},
async input => {
  const {output} = await prompt(input);
  return output!;
});
