import numpy as np
import torch 

def dyd_m_SBP(u, nx, dx, order = 4): #D+ = D- in SBP
    # summation-by-parts finite difference operators for first derivatives du/dx
    
    m = nx-1
    ux = np.zeros_like(u)
    
    # second order accurate case
    if order==2:
        # calculate partial derivatives on the boundaries:[0, m] using periodicity
        ux[0, :] = (u[1, :] -  u[m, :])/dx
        ux[m, :] = (u[0, :] -  u[m-1, :])/dx
        
        #calculate partial derivatives in the interior:(1:nx-1) using periodicity
        for j in range(1, m):
            ux[j, :] = (u[(j+1)%nx, :] -  u[(j-1)%nx, :])/(2.0*dx)

                   
    # fourth order accurate case        
    if order==4:
        ################################################# 
        # calculate partial derivatives on the boundaries:(0,1,2,3, : m-3, m-2, m-1, m)
        # with one-sided difference operators
        
        ux[0,:] = -24./17*u[0,:] + 59./34*u[1, :]  - 4./17*u[2, :] - 3./34*u[3,:]
        ux[1,:] = -1./2*u[0,:] + 1./2*u[2, :] ;
        ux[2,:] = 4./43*u[0,:] - 59./86*u[1, :]  + 59./86*u[3, :] - 4./43*u[4,:]
        ux[3,:] = 3./98*u[0,:] - 59./98*u[2, :]  + 32./49*u[4, :] - 4./49*u[5,:]


        ux[m,:] = 24./17*u[m,:] - 59./34*u[m-1, :]  + 4./17*u[m-2, :] + 3./34*u[m-3,:]
        ux[m-1,:] = 1./2*u[m,:] - 1./2*u[m-2, :] ;
        ux[m-2,:] = -4./43*u[m,:] + 59./86*u[m-1, :]- 59./86*u[m-3, :]+ 4./43*u[m-4,:]
        ux[m-3,:] = -3./98*u[m,:] + 59./98*u[m-2, :]- 32./49*u[m-4, :]+ 4./49*u[m-5,:]
    
                
        #------------------------------------------------------------------------------------------------------------------------------
        
        for i in range(4, m - 3):
            ux[i,:] = 0.083333333333333*u[i-2,:] - 0.666666666666667*u[i-1,:] + 0.666666666666667*u[i+1,:] - 0.083333333333333*u[i+2,:]

        ux[:,:] = ux/dx

    # sixth order accurate case        
    ################################################# 
       
    if order==6:
        # calculate partial derivatives on the boundaries:(0,1,2,3,4,5,6 : m-6, m-5, m-4, m-3, m-2, m-1, m)
        # with one-sided difference operators 
        ux[0,:] = -1.694834962162858*u[0,:] + 2.245634824947698*u[1,:] - 0.055649692295628*u[2,:] - 0.670383570370653*u[3,:] - 0.188774952148393*u[4,:] + 0.552135032829910*u[5,:] - 0.188126680800077*u[6,:]
        
        ux[1,:] = -0.434411786832708*u[0,:] + 0.107043134706685*u[2,:] + 0.420172642668695*u[3,:] + 0.119957288069806*u[4,:]    - 0.328691543801578*u[5,:] + 0.122487487014485*u[6,:] - 0.006557221825386*u[7,:]
        
        ux[2,:] = 0.063307644169533*u[0,:] - 0.629491308812471*u[1,:] + 0.809935419586724*u[3,:] - 0.699016381364484*u[4,:]   + 0.850345731199969*u[5,:] - 0.509589652965290*u[6,:] + 0.114508548186019*u[7,:]
        
        ux[3,:] = 0.110198643174386*u[0,:] - 0.357041083340051*u[1,:] - 0.117033418681039*u[2,:] + 0.120870009174558*u[4,:]+ 0.349168902725368*u[5,:] - 0.104924741749615*u[6,:] - 0.001238311303608*u[7,:]
        
        ux[4,:] = 0.133544619364965*u[0,:] - 0.438678347579289*u[1,:] + 0.434686341173840*u[2,:] - 0.520172867814934*u[3,:]  + 0.049912002176267*u[5,:] + 0.504693510958978*u[6,:] - 0.163985258279827*u[7,:]
        
        ux[5,:] = -0.127754693486067*u[0,:] + 0.393149407857401*u[1,:] - 0.172955234680916*u[2,:] - 0.491489487857764*u[3,:] - 0.016325050231672*u[4,:] + 0.428167552785852*u[6,:] - 0.025864364383975*u[7,:] + 0.013071869997141*u[8,:]
        
        ux[6,:] = 0.060008241515128*u[0,:] - 0.201971348965594*u[1,:] + 0.142885356631256*u[2,:] + 0.203603636754774*u[3,:] - 0.227565385120003*u[4,:] - 0.590259111130048*u[5,:] + 0.757462553894374*u[7,:] - 0.162184436527372*u[8,:] + 0.018020492947486*u[9,:]
        
        ux[7,:] = 0.009910488565285*u[1,:] - 0.029429452176588*u[2,:] + 0.002202493355677*u[3,:] + 0.067773581604826*u[4,:] + 0.032681945726690*u[5,:] - 0.694285851935105*u[6,:] + 0.743286642396343*u[8,:] - 0.148657328479269*u[9,:] + 0.016517480942141*u[10,:]

        ux[m-7,:] =-0.016517480942141*u[m-10,:] + 0.148657328479269*u[m-9,:] - 0.743286642396343*u[m-8,:] + 0.694285851935105*u[m-6,:] - 0.032681945726690*u[m-5,:] - 0.067773581604826*u[m-4,:] - 0.002202493355677*u[m-3,:] + 0.029429452176588*u[m-2,:]- 0.009910488565285*u[m-1,:]

        ux[m-6,:] =-0.018020492947486*u[m-9,:] + 0.162184436527372*u[m-8,:] - 0.757462553894374*u[m-7,:] + 0.590259111130048*u[m-5,:]+ 0.227565385120003*u[m-4,:] - 0.203603636754774*u[m-3,:] - 0.142885356631256*u[m-2,:] + 0.201971348965594*u[m-1,:]- 0.060008241515128*u[m,:]

        ux[m-5,:] =-0.013071869997141*u[m-8,:] + 0.025864364383975*u[m-7,:] - 0.428167552785852*u[m-6,:] + 0.016325050231672*u[m-4,:] + 0.491489487857764*u[m-3,:] + 0.172955234680916*u[m-2,:] - 0.393149407857401*u[m-1,:] + 0.127754693486067*u[m,:]

        ux[m-4,:] = 0.163985258279827*u[m-7,:] - 0.504693510958978*u[m-6,:] - 0.049912002176267*u[m-5,:] + 0.520172867814934*u[m-3,:]- 0.434686341173840*u[m-2,:] + 0.438678347579289*u[m-1,:] - 0.133544619364965*u[m,:]

        ux[m-3,:] = 0.001238311303608*u[m-7,:] + 0.104924741749615*u[m-6,:] - 0.349168902725368*u[m-5,:] - 0.120870009174558*u[m-4,:]+ 0.117033418681039*u[m-2,:] + 0.357041083340051*u[m-1,:] - 0.110198643174386*u[m,:]

        ux[m-2,:] =-0.114508548186019*u[m-7,:] + 0.509589652965290*u[m-6,:] - 0.850345731199969*u[m-5,:] + 0.699016381364484*u[m-4,:]- 0.809935419586724*u[m-3,:] + 0.629491308812471*u[m-1,:] - 0.063307644169533*u[m,:]

        ux[m-1,:] = 0.006557221825386*u[m-7,:] - 0.122487487014485*u[m-6,:] + 0.328691543801578*u[m-5,:] - 0.119957288069806*u[m-4,:]- 0.420172642668695*u[m-3,:] - 0.107043134706685*u[m-2,:] + 0.434411786832708*u[m,:]

        ux[m,:]   = 0.188126680800077*u[m-6,:] - 0.552135032829910*u[m-5,:] + 0.188774952148393*u[m-4,:] + 0.670383570370653*u[m-3,:] + 0.055649692295628*u[m-2,:] - 2.245634824947698*u[m-1,:] + 1.694834962162858*u[m,:]
        
        for i in range(8, m-7):
            ux[i,:] = -1/60*u[i-3,:] + 3/20*u[i-2,:] - 3/4*u[i-1,:] + 3/4*u[i+1,:] - 3/20*u[i+2,:] + 1/60*u[i+3,:]
    
        ux[:,:] = ux[:,:]/dx
    return torch.tensor(ux)
        
def dxd_m_SBP( u, ny , dy, order = 4):
    # summation-by-parts finite difference operators for first derivatives du/dy
    
    m = ny-1
    uy = np.zeros_like(u)


    if order == 2:
        uy[:,0]= u[:,1]-u[:,0]
        uy[: m] = u[:,m]-u[:,m-1]
        
        for j in range(1, m):
      
            uy[:, j] = 0.5*(u[:, j+1] - u[:, j-1])
   
        uy[:,:] = 1.0/dy*uy[:,:]

    if order == 4:
        
        uy[:, 0] = -24.0/17.0*u[:,0] + 59.0/34.0*u[:,1]  - 4.0/17.0*u[:, 2] - 3.0/34.0*u[:, 3]
        uy[:, 1] = -1.0/2.0*u[:,0] + 1.0/2.0*u[:,2] 
        uy[:, 2] = 4.0/43.0*u[:,0] - 59.0/86.0*u[:,1]  + 59.0/86.0*u[:,3] - 4.0/43.0*u[:,4]
        uy[:, 3] = 3.0/98.0*u[:,0] - 59.0/98.0*u[:,2]  + 32.0/49.0*u[:,4] - 4.0/49.0*u[:,5]

        uy[:, m] = 24.0/17.0*u[:,m] - 59.0/34.0*u[:,m-1]  + 4.0/17.0*u[:,m-2] + 3.0/34.0*u[:,m-3]
        uy[:, m-1] = 1.0/2.0*u[:,m] - 1.0/2.0*u[:,m-2] 
        uy[:, m-2] = -4.0/43.0*u[:,m] + 59.0/86.0*u[:,m-1]  - 59.0/86.0*u[:,m-3] + 4.0/43.0*u[:,m-4]
        uy[:, m-3] = -3.0/98.0*u[:,m] + 59.0/98.0*u[:,m-2]  - 32.0/49.0*u[:,m-4] + 4.0/49.0*u[:,m-5]

        for j in range(4, m-3):

            uy[:, j] = 1.0/12.0*u[:,j-2] - 2.0/3.0*u[:,j-1]  + 2.0/3.0*u[:,j+1] - 1.0/12.0*u[:,j+2]
    

        uy[:,:] = uy[:,:]/dy


    if order == 6:
        
        uy[:,0] = -1.694834962162858*u[:,0] + 2.245634824947698*u[:,1] - 0.055649692295628*u[:,2] - 0.670383570370653*u[:,3]  - 0.188774952148393*u[:,4] + 0.552135032829910*u[:,5] - 0.188126680800077*u[:,6]
        
        uy[:,1] = -0.434411786832708*u[:,0] + 0.107043134706685*u[:,2] + 0.420172642668695*u[:,3] + 0.119957288069806*u[:,4] - 0.328691543801578*u[:,5] + 0.122487487014485*u[:,6] - 0.006557221825386*u[:,7]
        
        uy[:,2] = 0.063307644169533*u[:,0] - 0.629491308812471*u[:,1] + 0.809935419586724*u[:,3] - 0.699016381364484*u[:,4]  + 0.850345731199969*u[:,5] - 0.509589652965290*u[:,6] + 0.114508548186019*u[:,7]
        
        uy[:,3] = 0.110198643174386*u[:,0] - 0.357041083340051*u[:,1] - 0.117033418681039*u[:,2] + 0.120870009174558*u[:,4]   + 0.349168902725368*u[:,5] - 0.104924741749615*u[:,6] - 0.001238311303608*u[:,7]
        
        uy[:,4] = 0.133544619364965*u[:,0] - 0.438678347579289*u[:,1] + 0.434686341173840*u[:,2] - 0.520172867814934*u[:,3] + 0.049912002176267*u[:,5] + 0.504693510958978*u[:,6] - 0.163985258279827*u[:,7]
        
        uy[:,5] = -0.127754693486067*u[:,0] + 0.393149407857401*u[:,1] - 0.172955234680916*u[:,2] - 0.491489487857764*u[:,3] - 0.016325050231672*u[:,4] + 0.428167552785852*u[:,6] - 0.025864364383975*u[:,7] + 0.013071869997141*u[:,8]
        
        uy[:,6] = 0.060008241515128*u[:,0] - 0.201971348965594*u[:,1] + 0.142885356631256*u[:,2] + 0.203603636754774*u[:,3] - 0.227565385120003*u[:,4] - 0.590259111130048*u[:,5] + 0.757462553894374*u[:,7] - 0.162184436527372*u[:,8]+ 0.018020492947486*u[:,9]
        
        uy[:,7] = 0.009910488565285*u[:,1] - 0.029429452176588*u[:,2] + 0.002202493355677*u[:,3] + 0.067773581604826*u[:,4]+ 0.032681945726690*u[:,5] - 0.694285851935105*u[:,6] + 0.743286642396343*u[:,8] - 0.148657328479269*u[:,9]+ 0.016517480942141*u[:,10]

        uy[:,m-7] =-0.016517480942141*u[:,m-10] + 0.148657328479269*u[:,m-9] - 0.743286642396343*u[:,m-8] + 0.694285851935105*u[:,m-6]- 0.032681945726690*u[:,m-5] - 0.067773581604826*u[:,m-4] - 0.002202493355677*u[:,m-3] + 0.029429452176588*u[:,m-2] - 0.009910488565285*u[:,m-1]

        uy[:,m-6] =-0.018020492947486*u[:,m-9] + 0.162184436527372*u[:,m-8] - 0.757462553894374*u[:,m-7] + 0.590259111130048*u[:,m-5]+ 0.227565385120003*u[:,m-4] - 0.203603636754774*u[:,m-3] - 0.142885356631256*u[:,m-2] + 0.201971348965594*u[:,m-1]- 0.060008241515128*u[:,m]

        uy[:,m-5] =-0.013071869997141*u[:,m-8] + 0.025864364383975*u[:,m-7] - 0.428167552785852*u[:,m-6] + 0.016325050231672*u[:,m-4] + 0.491489487857764*u[:,m-3] + 0.172955234680916*u[:,m-2] - 0.393149407857401*u[:,m-1] + 0.127754693486067*u[:,m]

        uy[:,m-4] = 0.163985258279827*u[:,m-7] - 0.504693510958978*u[:,m-6] - 0.049912002176267*u[:,m-5] + 0.520172867814934*u[:,m-3]- 0.434686341173840*u[:,m-2] + 0.438678347579289*u[:,m-1] - 0.133544619364965*u[:,m]

        uy[:,m-3] = 0.001238311303608*u[:,m-7] + 0.104924741749615*u[:,m-6] - 0.349168902725368*u[:,m-5] - 0.120870009174558*u[:,m-4]+ 0.117033418681039*u[:,m-2] + 0.357041083340051*u[:,m-1] - 0.110198643174386*u[:,m]

        uy[:,m-2] =-0.114508548186019*u[:,m-7] + 0.509589652965290*u[:,m-6] - 0.850345731199969*u[:,m-5] + 0.699016381364484*u[:,m-4]- 0.809935419586724*u[:,m-3] + 0.629491308812471*u[:,m-1] - 0.063307644169533*u[:,m]

        uy[:,m-1] = 0.006557221825386*u[:,m-7] - 0.122487487014485*u[:,m-6] + 0.328691543801578*u[:,m-5] - 0.119957288069806*u[:,m-4]- 0.420172642668695*u[:,m-3] - 0.107043134706685*u[:,m-2] + 0.434411786832708*u[:,m]

        uy[:,m]   = 0.188126680800077*u[:,m-6] - 0.552135032829910*u[:,m-5] + 0.188774952148393*u[:,m-4] + 0.670383570370653*u[:,m-3]+ 0.055649692295628*u[:,m-2] - 2.245634824947698*u[:,m-1] + 1.694834962162858*u[:,m]
                       
        for j in range(8, m-7):
            uy[:, j] = -0.016666666666666667*u[:,j-3] + 0.15*u[:,j-2] - 0.75*u[:,j-1] + 0.75*u[:,j+1] - 0.15*u[:,j+2] + 0.01666666666666667*u[:,j+3]
            
    
        uy[:,:] = (uy[:,:]/dy)
    return torch.tensor(uy)