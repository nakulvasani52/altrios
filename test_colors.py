import matplotlib.pyplot as plt
colors = ['#FF0000', '#0000FF', '#FF9900', '#24E780', '#00FFFF', '#FF00FF', '#993366', '#969696']
plt.figure(figsize=(10, 2))
for i, c in enumerate(colors):
    plt.fill_between([i, i+1], 0, 1, color=c)
plt.savefig('colors.png')
