'use server';
/**
 * @fileOverview Summarizes neuro-oncology images provided by the user.
 *
 * - summarizeImages - A function that handles the image summarization process.
 * - SummarizeImagesInput - The input type for the summarizeImages function.
 * - SummarizeImagesOutput - The return type for the summarizeImages function.
 */

import {ai} from '@/ai/ai-instance';
import {z} from 'genkit';

const SummarizeImagesInputSchema = z.object({
  imageDataUris: z
    .array(z.string())
    .describe(
      "An array of neuro-oncology images, as data URIs that must include a MIME type and use Base64 encoding. Expected format: 'data:<mimetype>;base64,<encoded_data>'."
    ),
  additionalContext: z.string().optional().describe('Any additional context or information about the images.'),
});
export type SummarizeImagesInput = z.infer<typeof SummarizeImagesInputSchema>;

const SummarizeImagesOutputSchema = z.object({
  summary: z.string().describe('A summarized interpretation of the key findings in the images.'),
});
export type SummarizeImagesOutput = z.infer<typeof SummarizeImagesOutputSchema>;

export async function summarizeImages(input: SummarizeImagesInput): Promise<SummarizeImagesOutput> {
  return summarizeImagesFlow(input);
}

const prompt = ai.definePrompt({
  name: 'summarizeImagesPrompt',
  input: {
    schema: z.object({
      imageDataUris: z
        .array(z.string())
        .describe(
          "An array of neuro-oncology images, as data URIs that must include a MIME type and use Base64 encoding. Expected format: 'data:<mimetype>;base64,<encoded_data>'."
        ),
      additionalContext: z.string().optional().describe('Any additional context or information about the images.'),
    }),
  },
  output: {
    schema: z.object({
      summary: z.string().describe('A summarized interpretation of the key findings in the images.'),
    }),
  },
  prompt: `You are an expert neuro-oncologist interpreting medical images.

  Based on the provided images and any additional context, provide a concise summary of the key findings. Focus on aspects relevant to neuro-oncology, such as potential tumors, abnormalities, or other significant observations.

  Additional Context: {{{additionalContext}}}
  Images:
  {{#each imageDataUris}}
  {{media url=this}}
  {{/each}}`,
});

const summarizeImagesFlow = ai.defineFlow<
  typeof SummarizeImagesInputSchema,
  typeof SummarizeImagesOutputSchema
>(
  {
    name: 'summarizeImagesFlow',
    inputSchema: SummarizeImagesInputSchema,
    outputSchema: SummarizeImagesOutputSchema,
  },
  async input => {
    const {output} = await prompt(input);
    return output!;
  }
);
