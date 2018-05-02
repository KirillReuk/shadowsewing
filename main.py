from functools import reduce
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

shadowImage = cv2.imread("bigshadows.png",0)
kernel = np.ones((5, 5), np.uint8)
shadowImage = cv2.morphologyEx(shadowImage, cv2.MORPH_OPEN, kernel)
# shadowImage = cv2.dilate(cv2.erode(shadowImage,kernel,iterations = 2),kernel,iterations = 2)

lidarImage = cv2.imread("biglidar.png", 0)
lidarBottomLevel = cv2.minMaxLoc(lidarImage)[0]


originalImage = Image.open("original.png")
emptyCanvas = Image.new("RGBA", (imgwidth, imgheight), (0, 0, 0, 0))
# emptyCanvas = np.zeros((imgheight,imgwidth,3), np.uint8)

houses = []
shadows = []

count = 0

#1. проходим по всем пикселям и собираем их в дома (связные области черного цвета)

queue = []
usedpixels = np.zeros((imgwidth + 2, imgheight + 2))


houseImage = cv2.copyMakeBorder(houseImage, top=1, bottom=1, left=1, right=1, borderType= cv2.BORDER_CONSTANT, value=255 ) #добавляем границу в 1 пиксель
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

# собираем точную высоту, вычисленную по лидару
housesexactheight = list(map(lambda house: reduce(lambda a, b: a + b, map(lambda p: lidarImage[p[1], p[0]] - lidarBottomLevel, house)) / len(house), houses))
# housesexactheight = []
# for house in houses:
#     sumpix = 0
#     for pix in house:
#         pixheight = lidarImage[pix[1], pix[0]] - lidarBottomLevel
#         sumpix += pixheight
#     sumpix = sumpix / len(house)
#     housesexactheight.append(sumpix)

# для каждого пикселя берем его лидарную высоту, берем среднее

print("step 2.5: exact height calculation complete")

#3. создаем лист пикселей теней для перебора
shadowpixels = np.zeros((imgwidth, imgheight))
shadowpixellist = []
for x in range(imgwidth):
    for y in range(imgheight):
        # pixel = shadowImage.getpixel((x, y))
        pixel = shadowImage[y][x]
        if pixel == 0:
            shadowpixels[x, y] = 1
            shadowpixellist.append((x, y))

print("step 3: shadow pixel collecting complete")

result = {}

#4. считаем тени
for ind, house in enumerate(houses):
    # берем дом, мапим через преобразование + pi/2, смотрим макс и мин
    d1 = max(zip(house, house), key=lambda x: distancefromsun(x[1], illuminationangle + math.pi / 2))[0]
    d2 = min(zip(house, house), key=lambda x: distancefromsun(x[1], illuminationangle + math.pi / 2))[0]

    currentshadowpixels = []
    currentshadowpixelcanvas = np.zeros((imgwidth + 2, imgheight + 2))
    for pixel in shadowpixellist:
        if shadowpixels[pixel[0], pixel[1]] == 1:
            angle1 = anglefromtwopoints(pixel, d1)
            angle2 = anglefromtwopoints(pixel, d2)
            if ((angle2 - angle1) % (2 * math.pi)) > math.pi:
                angle1, angle2 = angle2, angle1
            if angle2 < angle1:
                angle2 += 2 * math.pi

            if angle2 >= illuminationangle >= angle1:
                currentshadowpixels.append(pixel)
                currentshadowpixelcanvas[pixel[0], pixel[1]] = 1
                #emptyCanvas.putpixel(pixel, (255, 0, 0))

    for pixel in currentshadowpixels:
        shadowpixels[pixel[0], pixel[1]] = 0

    pivotshadow = []
    if len(currentshadowpixels) != 0:
        pivot = min(currentshadowpixels, key=lambda x: distancefromsun(x, illuminationangle))

        queue = []
        queue.append(pivot)

        while len(queue) > 0:
            cur = queue.pop(0)
            #for pixel in currentshadowpixels: #вместо перебора всех пикселей перебирать только соседние?
            for xshift, yshift in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
               if (0 <= cur[0] + xshift < imgwidth, 0 <= cur[1] + yshift < imgheight):
                    pixel = cur[0] + xshift, cur[1] + yshift

                    #if (pixel not in pivotshadow) & dopixelsneighbour(pixel, cur):
                    if (pixel not in pivotshadow) & (currentshadowpixelcanvas[pixel[0], pixel[1]] == 1):
                        queue.append(pixel)
                        pivotshadow.append(pixel)


    result[tuple(house[0])] = [house, pivotshadow] #словарь: ключи - верхние левые пиксели, значения - пары: пиксели дома, пиксели тени
    print("shadow", ind + 1, "/", len(houses), "cleanup complete", "(", round(100 * ind / len(houses), 3), "%)")

#рисуем результат
d = ImageDraw.Draw(emptyCanvas)
sumheight = 0
for ind, key in enumerate(result):
    for s in result[key][1]:
        emptyCanvas.putpixel(s, (255, 0, 255))
    for h in result[key][0]:
        emptyCanvas.putpixel(h, (0, 255, 0))

    farthestHousePix = max(result[key][0], key=lambda x: distancefromsun(x, illuminationangle))
    if len(result[key][1]) != 0:#у здания есть тень
        farthestShadowPix = max(result[key][1], key=lambda x: distancefromsun(x, illuminationangle))

        height = abs(distancebetweenpixels(farthestShadowPix, farthestHousePix) * imagescale - housesexactheight[ind])
        # height = housesexactheight[ind]
    else:#у здания нет тени
        height = 0

    sumheight += height
    d.text(key, str(round(height, 1)))

print(len(houses))
print("average error: ", sumheight / len(houses))

emptyCanvas.show()
#originalImage.paste(emptyCanvas, (0, 0), emptyCanvas)
#originalImage.show()