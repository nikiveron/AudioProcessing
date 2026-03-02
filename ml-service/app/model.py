import torch.nn as nn

class GRUSeparator(nn.Module):
    def __init__(self, input_size=128, hidden_size=128, num_layers=2):
        super(GRUSeparator, self).__init__()
        self.gru = nn.GRU(input_size=input_size, hidden_size=hidden_size,
                          num_layers=num_layers, batch_first=True, bidirectional=True, dropout=0.3)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_size, input_size)
        )

    def forward(self, x):
        x = x.squeeze(1).permute(0, 2, 1)  # (batch, time, freq)
        out, _ = self.gru(x)
        out = self.fc(out)
        out = out.permute(0, 2, 1).unsqueeze(1)
        return out
