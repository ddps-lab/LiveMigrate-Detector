import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import time


class SimpleNet(nn.Module):
    def __init__(self):
        super(SimpleNet, self).__init__()
        self.fc1 = nn.Linear(10, 50)
        self.fc2 = nn.Linear(50, 20)
        self.fc3 = nn.Linear(20, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x


while True:
    model = SimpleNet()
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    X = torch.randn(100, 10)
    y = torch.randn(100, 1)

    for epoch in range(50):
        optimizer.zero_grad()
        outputs = model(X)
        loss = criterion(outputs, y)
        loss.backward()
        optimizer.step()

        if epoch % 10 == 0:
            print(f"Epoch {epoch}, Loss: {loss.item():.4f}", flush=True)

    with torch.no_grad():
        test_input = torch.randn(5, 10)
        predictions = model(test_input)
        print(
            f"Test predictions: {predictions.flatten().tolist()}", flush=True)

    conv_model = nn.Sequential(
        nn.Conv2d(1, 32, 3),
        nn.ReLU(),
        nn.Conv2d(32, 64, 3),
        nn.ReLU(),
        nn.AdaptiveAvgPool2d((1, 1)),
        nn.Flatten(),
        nn.Linear(64, 10)
    )

    dummy_input = torch.randn(1, 1, 28, 28)
    conv_output = conv_model(dummy_input)
    print(f"Conv model output shape: {conv_output.shape}", flush=True)

    time.sleep(5)
