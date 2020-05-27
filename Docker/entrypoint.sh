#!/bin/sh
##watch for windows lineendings before you paste the script again...
##Here we go the 7 stages of grief
echo "================1===================="
mkdir /installbot
echo "================2===================="
BOT_GITHUB=`grep BOT_GITHUB /app/blackorderbot.conf |  cut -d " " -f3-`
git config --global url."https://$BOT_GITHUB:@github.com/".insteadOf "https://github.com/"
echo "================3===================="
git clone https://github.com/AciDCooL/BlackOrderBot.git /installbot
echo "================4===================="
cp -rT /installbot /app
rm -rf /installbot
echo "================5===================="
chmod 755 /app/ffmpeg
echo "================6===================="
# start cron
/usr/sbin/crond -f -l 8 &
echo "================7===================="
python -u /app/bot.py
