import math

class Quat:
    def __init__(self):
        self.q = [1.0, 0.0, 0.0, 0.0]
        self.pq = [1.0, 0.0, 0.0, 0.0]

    def update_quat(self, w, t):
        rvec = [ w['wx'] * t, w['wy'] * t, w['wz'] * t ]   
        fetarad = math.sqrt(rvec[0] * rvec[0] + rvec[1] * rvec[1] + rvec[2] * rvec[2])
        fetarad2 = fetarad * fetarad

        if fetarad2 < 0.02:
            sinhalfeta = fetarad * (0.5 - 0.02083333333 * fetarad2)
        elif fetarad2 < 0.06:
            fetarad4 = fetarad2 * fetarad2
            sinhalfeta = fetarad * (0.5 - 0.02083333333 * fetarad2 + 0.0002604166667 * fetarad4)
        else:
            sinhalfeta = math.sin(0.5 * fetarad)


        if fetarad != 0.0:
            ftmp = sinhalfeta / fetarad
            self.pq[1] = rvec[0] * ftmp		
            self.pq[2] = rvec[1] * ftmp		
            self.pq[3] = rvec[2] * ftmp		
        else:
            self.pq[1] = 0.0
            self.pq[2] = 0.0
            self.pq[3] = 0.0

        fvecsq = self.pq[1] * self.pq[1] + self.pq[2] * self.pq[2] + self.pq[3] * self.pq[3]
	    
        if fvecsq <= 1.0:
            self.pq[0] = math.sqrt(1.0 - fvecsq)
        else: 
            self.pq[0] = 0.0

        tmpq = [0.0, 0.0, 0.0, 0.0 ]
        tmpq[0] = self.q[0]*self.pq[0] - self.q[1]*self.pq[1] - self.q[2]*self.pq[2] - self.q[3]*self.pq[3]
        tmpq[1] = self.q[0]*self.pq[1] + self.pq[0]*self.q[1] + self.q[2]*self.pq[3] - self.q[3]*self.pq[2]
        tmpq[2] = self.q[0]*self.pq[2] + self.pq[0]*self.q[2] + self.q[3]*self.pq[1] - self.q[1]*self.pq[3]
        tmpq[3] = self.q[0]*self.pq[3] + self.pq[0]*self.q[3] + self.q[1]*self.pq[2] - self.q[2]*self.pq[1]


        qMag = math.sqrt(tmpq[0] * tmpq[0] + tmpq[1] * tmpq[1] + tmpq[2] * tmpq[2] + tmpq[3] * tmpq[3])
        
        if qMag == 0.0:
            pass
        elif self.q[0] < 0.0:
            qMag = -1*qMag
        
        if qMag > 0.0: 
            self.q[0] = tmpq[0]/qMag
            self.q[1] = tmpq[1]/qMag
            self.q[2] = tmpq[2]/qMag        
            self.q[3] = tmpq[3]/qMag

    def to_matrix4(self):
        w = self.q[0]
        x = self.q[1]
        y = self.q[2]
        z = self.q[3]

        x2 = x + x
        y2 = y + y
        z2 = z + z        
        xx = x * x2
        xy = x * y2
        xz = x * z2
        yy = y * y2
        yz = y * z2
        zz = z * z2
        wx = w * x2
        wy = w * y2
        wz = w * z2

        m = [[0.0, 0.0, 0.0, 0.0],
             [0.0, 0.0, 0.0, 0.0],
             [0.0, 0.0, 0.0, 0.0],
             [0.0, 0.0, 0.0, 0.0]]

        m[0][0] = 1.0 - (yy + zz)
        m[0][1] = xy + wz
        m[0][2] = xz - wy
        m[0][3] = 0.0

        m[1][0] = xy - wz
        m[1][1] = 1.0 - (xx + zz)
        m[1][2] = yz + wx
        m[1][3] = 0.0

        m[2][0] = xz + wy
        m[2][1] = yz - wx
        m[2][2] = 1.0 - (xx + yy)
        m[2][3] = 0.0

        m[3][0] = 0.0
        m[3][1] = 0.0
        m[3][2] = 0.0
        m[3][3] = 1.0

        return m

    def print_rpy(self, mtx):
        thetaX = math.asin(mtx[1][2])
        thetaY = 0.0;
        thetaZ = 0.0;

        if thetaX < math.pi/2:
            if thetaX > -1 * math.pi/2:
                thetaZ = math.atan2(-mtx[1][0], mtx[1][1])
                thetaY = math.atan2(-mtx[0][2], mtx[2][2])
            else:
                thetaZ = -1 * math.atan2(mtx[2][0], mtx[0][0])
                thetaY = 0.0
        else:
            thetaZ = math.atan2(mtx[2][0], mtx[0][0])
            thetaY = 0.0

        hdgDegrees = 57.29 * thetaY
        pitchDegrees = 57.29 * thetaX
        rollDegrees = 57.29 * thetaZ

        print('{0:2.3f},{1:2.3f},{2:2.3f}'.format(hdgDegrees,pitchDegrees,rollDegrees))
    
    def print_euler(self):
        
        eroll  = 57.29 * math.atan2(2.0 * (self.q[3] * self.q[2] + self.q[0] * self.q[1]) , 1.0 - 2.0 * (self.q[1] * self.q[1] + self.q[2] * self.q[2]))
        epitch = 57.29 * math.asin(2.0 * (self.q[2] * self.q[0] - self.q[3] * self.q[1]))
        eyaw   = 57.29 * math.atan2(2.0 * (self.q[3] * self.q[0] + self.q[1] * self.q[2]) , - 1.0 + 2.0 * (self.q[0] * self.q[0] + self.q[1] * self.q[1]))

        print('{0:2.3f},{1:2.3f},{2:2.3f}'.format(eroll,epitch,eyaw))
