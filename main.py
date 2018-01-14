from PIL import Image
from PIL import ImageDraw
import math
import numpy as np
import cv2

def dopixelsneighbour(pixel1, pixel2):
    diffx = abs(pixel1[0] - pixel2[0])
    diffy = abs(pixel1[1] - pixel2[1])
    return (diffx < 2) & (diffy < 2)

def distancefromsun(pixel, angle):
    return pixel[0] * math.cos(angle) - pixel[1] * math.sin(angle)

def distancebetweenpixels(pixel1, pixel2):
    return math.sqrt((pixel1[0] - pixel2[0]) * (pixel1[0] - pixel2[0]) + (pixel1[1] - pixel2[1]) * (pixel1[1] - pixel2[1]))

def reversecolor(color):
    return 255 - color[0], 255 - color[1], 255 - color[2]

def anglefromtwopoints(point1, point2):
    return math.atan2(point2[1] - point1[1], point1[0] - point2[0])

def imageToData(funImage):
    if funImage.mode != "RGB":
        funImage = Image.merge("RGB", funImage.split()[:-1])

    funData = np.reshape(list(funImage.getdata()), (funImage.size[0], funImage.size[1], 3)).tolist()

    return funData

illuminationangle = 1.6
imagescale = 1

houseImage = cv2.imread("bighouses.png",0)
imgheight, imgwidth = houseImage.shape
imgsize = imgheight * imgwidth
houseImage=cv2.copyMakeBorder(houseImage, top=1, bottom=1, left=1, right=1, borderType= cv2.BORDER_CONSTANT, value=255 ) #добавляем границу в 1 пиксель

shadowImage = cv2.imread("bigshadows.png",0)
kernel = np.ones((5,5),np.uint8)
shadowImage = cv2.morphologyEx(shadowImage, cv2.MORPH_OPEN, kernel)
#shadowImage = cv2.dilate(cv2.erode(shadowImage,kernel,iterations = 2),kernel,iterations = 2)


originalImage = Image.open("original.png")
emptyCanvas = Image.new("RGBA", (imgheight, imgwidth), (0, 0, 0, 0))
#emptyCanvas = np.zeros((imgheight,imgwidth,3), np.uint8)

houses = []
shadows = []

count = 0

#1. проходим по всем пикселям и собираем их в дома (связные области черного цвета)

queue = []
usedpixels = np.zeros((imgwidth + 2, imgheight + 2))


for x in range(1, imgwidth + 1):
    for y in range(1, imgheight + 1):

        count += 1
        print("total", count, "of", imgsize, "(", round(100 * count / imgsize, 3), "%)")

        if houseImage[y, x] == 0:
            if usedpixels[x, y] == 0:
                usedpixels[x, y] = 1  # найден новый дом
                queue.append((x, y))
                house = []

                while len(queue) > 0: #через flood fill собираем этот дом по пикселям
                    print("queue length:", len(queue), "top pixel:", queue[0])
                    cur = queue.pop(0)
                    house.append((cur[0] - 1, cur[1] - 1)) #вычитаем 1 из-за добавленной границы
                    for xshift, yshift in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
                        if (usedpixels[cur[0] + xshift, cur[1] + yshift] == 0) & (houseImage[cur[1] + yshift, cur[0] + xshift] == 0):
                                usedpixels[cur[0] + xshift, cur[1] + yshift] = 1
                                queue.append((cur[0] + xshift, cur[1] + yshift))

                houses.append(house)

print("step 1: housalization complete")

#2. сортируем дома по самой удаленной от солнца точке
houses.sort(key=lambda x: max(map(lambda y: distancefromsun(y, illuminationangle), x)), reverse=True)

print("step 2: house sorting complete")

#3. создаем лист пикселей теней для перебора
shadowpixels = []
for x in range(imgwidth):
    for y in range(imgheight):
        # pixel = shadowImage.getpixel((x, y))
        pixel = shadowImage[y][x]
        if pixel == 0:
            shadowpixels.append((x, y))

print("step 3: shadow pixel collecting complete")

result = {}

#4. считаем тени
for ind, house in enumerate(houses):
    # берем дом, мапим через преобразование + pi/2, смотрим макс и мин
    d1 = max(zip(house, house), key=lambda x: distancefromsun(x[1], illuminationangle + math.pi / 2))[0]
    d2 = min(zip(house, house), key=lambda x: distancefromsun(x[1], illuminationangle + math.pi / 2))[0]

    currentshadowpixels = []
    for pixel in shadowpixels:
        angle1 = anglefromtwopoints(pixel, d1)
        angle2 = anglefromtwopoints(pixel, d2)
        if ((angle2 - angle1) % (2 * math.pi)) > math.pi:
            angle1, angle2 = angle2, angle1
        if angle2 < angle1:
            angle2 += 2 * math.pi

        if angle2 >= illuminationangle >= angle1:
            currentshadowpixels.append(pixel)
            #emptyCanvas.putpixel(pixel, (255, 0, 0))

    for pixel in currentshadowpixels:
        shadowpixels.remove(pixel)

    pivotshadow = []
    if len(currentshadowpixels) != 0:
        pivot = min(currentshadowpixels, key=lambda x: distancefromsun(x, illuminationangle))

        queue = []
        queue.append(pivot)

        while len(queue) > 0:
            cur = queue.pop(0)
            for pixel in currentshadowpixels:
                if (pixel not in pivotshadow) & dopixelsneighbour(pixel, cur):
                    queue.append(pixel)
                    pivotshadow.append(pixel)


    result[tuple(house[0])] = [house, pivotshadow] #словарь: ключи - верхние левые пиксели, значения - пары: пиксели дома, пиксели тени
    print("shadow", ind, "/", len(houses), "cleanup complete")

#рисуем результат
d = ImageDraw.Draw(emptyCanvas)
for key in result:
    for s in result[key][1]:
        emptyCanvas.putpixel(s, (255, 0, 255))
    for h in result[key][0]:
        emptyCanvas.putpixel(h, (0, 255, 0))

    farthestHousePix = max(result[key][0], key=lambda x: distancefromsun(x, illuminationangle))
    if len(result[key][1]) != 0:#у здания есть тень
        farthestShadowPix = max(result[key][1], key=lambda x: distancefromsun(x, illuminationangle))

        height = distancebetweenpixels(farthestShadowPix, farthestHousePix) * imagescale
    else:#у здания нет тени
        height = 0

    d.text(key, str(round(height, 2)))
print(len(houses))

emptyCanvas.show()
#originalImage.paste(emptyCanvas, (0, 0), emptyCanvas)
#originalImage.show()