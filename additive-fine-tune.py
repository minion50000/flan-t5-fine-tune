import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
from transformers import TextDataset
from transformers import T5ForConditionalGeneration, T5Tokenizer, DataCollatorForLanguageModeling, Trainer, TrainingArguments
import torch.nn.functional as F

class T5FineTuner(nn.Module):
    def __init__(self):
        super(T5FineTuner, self).__init__()
        self.t5model = T5ForConditionalGeneration.from_pretrained('google/flan-t5-base').to('cuda')
        for param in self.t5model.parameters():
            param.requires_grad = False
        self.linear_relu_stack = nn.Sequential(
            nn.Linear(32128, 8000),
            nn.ReLU(),
            nn.Linear(8000, 8000),
            nn.ReLU(),
            nn.Linear(8000, 32128)
        )
    def forward(self, input_ids, attention_mask=None, decoder_input_ids=None, decoder_attention_mask=None, labels=None):
        outputs = self.t5model(
            input_ids,
            attention_mask=attention_mask,
            decoder_input_ids=decoder_input_ids,
            decoder_attention_mask=decoder_attention_mask,
            labels=labels
        )
        logits = self.linear_relu_stack(outputs.logits)
        return logits

tokenizer = T5Tokenizer.from_pretrained('google/flan-t5-base')
model = T5FineTuner().to('cuda')

train_path = 'bittensor.txt'
train_dataset = TextDataset(tokenizer=tokenizer, file_path=train_path, block_size=512)
num_epochs = 30
data_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
loss_fn = nn.CrossEntropyLoss(ignore_index=tokenizer.pad_token_id)
#print(train_dataset.examples)
from torch.optim import Adam

# Create an optimizer with only the new parameters
optimizer = Adam(model.linear_relu_stack.parameters(), lr=1e-4)

# Example pseudo-training loop
for epoch in range(num_epochs):
    for batch in data_loader:
        inputs = batch
        labels = batch
        print('inputs : ', inputs.shape)
        optimizer.zero_grad()
        outputs = model(inputs.to('cuda'), labels = batch.to('cuda'))
        print('output : ', outputs.shape)
        print('labels : ', labels.shape)
        #loss = loss_fn(outputs, labels)
        mask = (labels != tokenizer.pad_token_id).float().to('cuda')
        labels = F.one_hot(labels, num_classes=32128).to('cuda').float()
        #loss = F.cross_entropy(outputs, labels, reduction = 'none')
        loss = [F.cross_entropy(output, label, reduction = 'none') for output, label in zip(outputs, labels)]
        loss = torch.stack(loss).to('cuda')
        print('loss : ', loss.shape)
        print('mask : ', mask.shape)
        masked_loss = (loss * mask).mean(dim=1)
        masked_loss.backward()
        optimizer.step()


input_text = "What is bittensor?"
# Encode the input text to tensor
input_ids = tokenizer.encode(input_text, return_tensors='pt').to('cuda')
# Generate text using the model. Adjust the max_length as needed.
output_ids = model.generate(input_ids, max_length=100, num_beams=5, early_stopping=True)

# Decode the generated ids to text
generated_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)

print("Input Text:", input_text)
print("Generated Text:", generated_text)
